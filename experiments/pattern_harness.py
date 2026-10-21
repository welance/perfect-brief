"""The deterministic harness for brief_bar/patterns: both engines, one corpus.

Validates the catalogue (portable regex dialect, ids, limits) and the labelled
corpus, runs the Python runtime and the JavaScript runtime (through node) on
the same bytes, and fails on any label mismatch, any engine disagreement, or
any pattern slow enough to suggest catastrophic backtracking.

    python -m experiments.pattern_harness [--catalogue P] [--cases P] [--json]

Missing node is a failure, not a skip: parity is the point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from brief_bar.patterns import CASES_PATH, CATALOGUE_PATH, Catalogue

ROOT = Path(__file__).resolve().parent.parent
NODE_RUNNER = ROOT / "experiments" / "pattern_node.mjs"
LOCALES = ("en-GB", "it", "de", "fr", "es", "ar", "pt", "pt-BR", "nl", "pl", "zh-Hans", "ja")
KINDS = ("email", "url", "phone")
ORIGINS = ("human", "ai-proposed")
SLOW_MS = 1500.0
# Inputs shaped to make a backtracking regex go quadratic or worse.
ADVERSARIAL = {
    "digits": "0" * 50_000,
    "spaced-digits": "1 " * 25_000,
    "dashed-plus": "+" + "1-" * 20_000,
    "at-run": "a" * 50_000 + "@",
    "url-dots": "http://" + "a." * 20_000,
    "currency-run": "€" + "1 " * 20_000,
    "dotted-groups": "123." * 15_000,
    "parens": "+1 " + "(1)" * 15_000,
}


def dialect_errors(source: str) -> list[str]:
    """The common subset of Python `re` and JS RegExp (no `u` flag) we allow."""
    errs = []
    banned = {
        "d": r"\d", "D": r"\D", "w": r"\w", "W": r"\W", "s": r"\s", "S": r"\S",
        "b": r"\b", "B": r"\B", "p": r"\p", "P": r"\P", "A": r"\A", "Z": r"\Z", "z": r"\z",
    }  # fmt: skip
    i, in_class = 0, False
    while i < len(source):
        ch = source[i]
        if ch == "\\":
            nxt = source[i + 1 : i + 2]
            if nxt in banned:
                errs.append(f"{banned[nxt]} differs between engines; spell the class out")
            elif nxt.isdigit() and nxt != "0":
                errs.append("backreferences are not allowed")
            elif nxt in ("x", "N", "k", "g"):
                errs.append(f"\\{nxt} is not portable")
            i += 2
            continue
        if in_class:
            if ch == "]":
                in_class = False
        elif ch == "[":
            in_class = True
            if source[i + 1 : i + 2] == "]" or source[i + 1 : i + 3] == "^]":
                errs.append("empty or ']'-leading character class is not portable")
        elif ch == ".":
            errs.append("unescaped '.' differs on line terminators; use an explicit class")
        elif ch == "$":
            errs.append("'$' differs on a trailing newline; use a negative lookahead")
        elif ch == "(" and source[i + 1 : i + 2] == "?":
            if source[i + 2 : i + 3] not in (":", "=", "!"):
                errs.append("only (?: (?= (?! groups are portable")
        elif ch == ")" and re.match(r"[+*]|\{[0-9]+,\}", source[i + 1 :]):
            # a repeated group with no upper bound is how a regex goes
            # exponential; every group repetition must be bounded
            errs.append("unbounded repetition of a group; use {m,n}")
        i += 1
    return errs


def validate(cat: dict, cases: list[dict]) -> list[str]:
    errs: list[str] = []
    for key in ("schema_version", "version", "contacts", "exclusions", "keywords"):
        if key not in cat:
            errs.append(f"catalogue: missing {key}")
    if errs:
        return errs
    ids: set[str] = set()
    for e in cat["contacts"] + cat["exclusions"]:
        pid = e.get("id", "?")
        if pid in ids:
            errs.append(f"{pid}: duplicate id")
        ids.add(pid)
        if set(e.get("flags", "")) - {"i"}:
            errs.append(f"{pid}: only the 'i' flag is portable")
        errs += [f"{pid}: {m}" for m in dialect_errors(e.get("source", ""))]
        try:
            rx = re.compile(e["source"])
        except (re.error, KeyError) as exc:
            errs.append(f"{pid}: does not compile: {exc}")
            continue
        if rx.groups > 1:
            errs.append(f"{pid}: at most one capturing group (the span)")
        if rx.search("") is not None:
            errs.append(f"{pid}: matches the empty string")
    for e in cat["contacts"]:
        pid = e.get("id", "?")
        if e.get("kind") not in KINDS:
            errs.append(f"{pid}: kind must be one of {KINDS}")
        if not isinstance(e.get("priority"), int):
            errs.append(f"{pid}: priority must be an integer")
        if ("min_digits" in e) != ("max_digits" in e):
            errs.append(f"{pid}: min_digits and max_digits go together")
    for group in ("data", "compliance"):
        kws = cat["keywords"].get(group, [])
        if not kws:
            errs.append(f"keywords.{group}: empty")
        for k in kws:
            if k != k.lower() or not k.strip():
                errs.append(f"keywords.{group}: {k!r} must be non-empty lowercase")
        if len(set(kws)) != len(kws):
            errs.append(f"keywords.{group}: duplicates")
    seen: set[str] = set()
    for c in cases:
        cid = c.get("id", "?")
        if cid in seen:
            errs.append(f"case {cid}: duplicate id")
        seen.add(cid)
        if c.get("locale") not in LOCALES:
            errs.append(f"case {cid}: locale {c.get('locale')!r} is not a service locale")
        if c.get("origin") not in ORIGINS:
            errs.append(f"case {cid}: origin must be one of {ORIGINS}")
        try:
            expected_spans(c)
        except ValueError as exc:
            errs.append(f"case {cid}: {exc}")
    missing = set(LOCALES) - {c.get("locale") for c in cases}
    if missing:
        errs.append(f"corpus: no case for {sorted(missing)}")
    return errs


def expected_spans(case: dict) -> list[list]:
    """Labels are [kind, text] in document order; offsets are derived."""
    out, pos = [], 0
    for kind, text in case["spans"]:
        if kind not in KINDS:
            raise ValueError(f"span kind {kind!r}")
        at = case["text"].find(text, pos)
        if at < 0 or not text:
            raise ValueError(f"span {text!r} not found after offset {pos}")
        out.append([kind, at, at + len(text), text])
        pos = at + len(text)
    return out


def run_python(cat: Catalogue, texts: dict[str, str]) -> dict[str, dict]:
    out = {}
    for cid, text in texts.items():
        t0 = time.perf_counter()
        spans = [[s.kind, s.start, s.end, s.text] for s in cat.contact_spans(text)]
        out[cid] = {
            "spans": spans,
            "data": bool(cat.keyword_hits(text, "data")),
            "compliance": bool(cat.keyword_hits(text, "compliance")),
            "ms": (time.perf_counter() - t0) * 1000,
        }
    return out


def run_node(catalogue_path: Path, texts: dict[str, str], timeout: float = 120) -> dict[str, dict]:
    proc = subprocess.run(
        ["node", str(NODE_RUNNER), str(catalogue_path)],
        input=json.dumps(texts),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return json.loads(proc.stdout)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(catalogue_path: Path = CATALOGUE_PATH, cases_path: Path = CASES_PATH) -> dict:
    """The deterministic report; `ok` is the only thing a caller must read."""
    cat_data = json.loads(catalogue_path.read_text(encoding="utf-8"))
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    report: dict = {
        "catalogue": {"version": cat_data.get("version"), "sha256": _sha(catalogue_path)},
        "cases": {"count": len(cases), "sha256": _sha(cases_path)},
        "invalid": validate(cat_data, cases),
        "failures": [],
        "disagreements": [],
        "slow": [],
    }
    if report["invalid"]:
        report["ok"] = False
        return report
    cat = Catalogue(cat_data)
    texts = {c["id"]: c["text"] for c in cases}
    py, js = run_python(cat, texts), run_node(catalogue_path, texts)
    for c in cases:
        cid = c["id"]
        want = {"spans": expected_spans(c)}
        for cue in ("data", "compliance"):
            if cue in c:
                want[cue] = c[cue]
        for engine, got in (("python", py[cid]), ("node", js[cid])):
            for key, value in want.items():
                if got[key] != value:
                    report["failures"].append(
                        {"case": cid, "engine": engine, "field": key, "want": value, "got": got[key]}
                    )
        for key in ("spans", "data", "compliance"):
            if py[cid][key] != js[cid][key]:
                report["disagreements"].append(
                    {"case": cid, "field": key, "python": py[cid][key], "node": js[cid][key]}
                )
    adv_py, adv_js = run_python(cat, ADVERSARIAL), run_node(catalogue_path, ADVERSARIAL)
    for name in ADVERSARIAL:
        for engine, got in (("python", adv_py[name]), ("node", adv_js[name])):
            if got["ms"] > SLOW_MS:
                report["slow"].append({"input": name, "engine": engine, "ms": round(got["ms"])})
        if adv_py[name]["spans"] != adv_js[name]["spans"]:
            report["disagreements"].append({"case": f"adversarial:{name}", "field": "spans"})
    report["ok"] = not (report["failures"] or report["disagreements"] or report["slow"])
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--catalogue", type=Path, default=CATALOGUE_PATH)
    ap.add_argument("--cases", type=Path, default=CASES_PATH)
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args(argv)
    report = evaluate(args.catalogue, args.cases)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for line in report["invalid"]:
            print(f"INVALID  {line}")
        for f in report["failures"]:
            print(f"FAIL     {f['case']} [{f['engine']}] {f['field']}: want {f['want']} got {f['got']}")
        for d in report["disagreements"]:
            print(f"DIVERGE  {d['case']} {d['field']}")
        for s in report["slow"]:
            print(f"SLOW     {s['input']} [{s['engine']}] {s['ms']} ms")
        status = "ok" if report["ok"] else "FAILED"
        print(
            f"{status}: catalogue {report['catalogue']['version']}, {report['cases']['count']} cases, 2 engines"
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

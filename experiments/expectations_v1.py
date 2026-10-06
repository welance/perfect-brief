"""Load an opt-in candidate ruleset without changing the bundled service rules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

from brief_bar import aggregate, llm, load_bundled, loader
from brief_bar.score import load_rules

DATA = Path(__file__).with_name("expectations-v1")
NEW_RULE = "scope-resource-alignment"
NEW_WEIGHT = 10.0


def load_variant():
    baseline, cfg = load_bundled()
    overrides = load_rules(str(DATA / "rules"))
    criteria_only = {rid: overrides.get(rid, rule) for rid, rule in baseline.items()}
    candidate = {rid: replace(rule, weight=rule.weight * 0.9) for rid, rule in criteria_only.items()}
    candidate[NEW_RULE] = replace(overrides[NEW_RULE], weight=NEW_WEIGHT)
    return baseline, criteria_only, candidate, cfg


def version() -> str:
    digest = hashlib.sha256(loader.ruleset_version().encode())
    digest.update(Path(__file__).read_bytes())
    for path in sorted((DATA / "rules").glob("*.yaml")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return f"1.2.0-expectations.1+{digest.hexdigest()[:12]}"


def evaluate(raw: str, source: str) -> dict:
    baseline, criteria_only, candidate, cfg = load_variant()
    verdicts = llm.parse_judge(candidate, raw, source)
    old_ids = [v for v in verdicts if v.rule_id in baseline]
    results = {}
    for name, rules, judged in [
        ("revised_criteria_original_weights", criteria_only, old_ids),
        ("candidate_with_new_rule", candidate, verdicts),
    ]:
        results[name] = {
            context: asdict(aggregate(judged, rules, cfg, contexts=tags))
            for context, tags in [("directory", None), ("generic", [])]
        }
    return {
        "experiment_version": version(),
        "baseline_version": loader.ruleset_version(),
        "weights": {rid: rule.weight for rid, rule in candidate.items()},
        "results": results,
        "verdicts": json.loads(raw),
    }

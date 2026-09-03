"""briefs.welance.com — the Brief Bar scoring service.

Score is how good a brief is; a separate gate is whether it may publish. The
LLM only judges (server-side, key never leaves the box); code owns every number,
the gate, and the decision. The bundled console at / is the playground.
"""

from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from brief_bar.llm import JudgeUnparsable

from . import cache, llm_client, mcp_http, scorer
from .llm_client import JudgeTruncated, LLMNotConfigured, ModelNotAllowed
from .models import (
    Health,
    ModelsResponse,
    ReferenceOut,
    RuleOut,
    RulesResponse,
    ScoreRequest,
    ScoreResponse,
    SuggestAllRequest,
    Suggestion,
    SuggestRequest,
)
from .settings import settings
from .version import SERVICE_VERSION

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("brief_bar.api")

# The one public surface: the same site/ that GitHub Pages publishes.
# Landing at /, console.html, rules.html, welance.css, animations/.
SITE = Path(__file__).resolve().parent.parent / "site"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    log.info(
        "ruleset %s · %d rules · LLM configured: %s",
        scorer.version(),
        len(scorer.rules()),
        llm_client.configured(),
    )
    try:
        # the hosted MCP connector's session manager lives and dies with the app
        async with mcp_http.server.session_manager.run():
            yield
    finally:
        await llm_client.close_openrouter_client()
        await cache.close()


API_DESCRIPTION = """
**What this is.** A brief is the text a client hands a team before any work starts.
This service reads one and answers two separate questions:

- **How good is it?** A *score* from 0 to 100: a weighted average over fourteen
  public rules (is there a real problem statement, named users, a measurable
  outcome, a budget, a deadline…). Weights are public and sum to 100.
- **May it publish?** A *gate* of four hard requirements. A brief that fails the
  gate is *blocked* whatever its score, because a brilliant brief that names the
  client cannot go on a blind noticeboard.

**How the number is made.** A model only *judges*: for each rule it says pass,
partial or fail, with a verbatim quote from the brief as evidence. Deterministic
code then owns every number, the gate and the decision. The model never touches
a weight. Every answer carries the `ruleset_version` that judged it, so the same
brief and the same version give the same verdict later.

**Two judges.** `judge: "mock"` is a keyword stub that runs without any model
(English only, useful offline and in CI). `judge: "llm"` is the real judge on
the service's own model account, rate-limited per address. Send your own
OpenRouter key in `x-llm-key` and the call runs on your account instead: no
rate limit, no cache, any allowed model.

**Typical flow.** `POST /v1/score` → read `gate.missing` first, fix those →
`POST /v1/suggest/all` for ready-to-paste sentences → score again → stop when
`decision` is `accepted`. The rules themselves are at `GET /v1/rules` and, as
files, at https://github.com/welance/perfect-brief.

No account, no cookies, nothing stored beyond a one-day verdict cache. What
travels where is written out at https://briefs.welance.com/data.html.
"""

TAGS = [
    {
        "name": "score",
        "description": "The one call that matters: a brief in, score + gate + fourteen verdicts out.",
    },
    {
        "name": "fixes",
        "description": "Ready-to-paste sentences for the rules a brief fails, written in the brief's language and checked by a second model.",
    },
    {
        "name": "ruleset",
        "description": "The bar itself: every rule, its weight, its criteria and its sources, with the version that ties them together.",
    },
    {
        "name": "meta",
        "description": "Is the service up, which judge is configured, which models a request may name.",
    },
]

app = FastAPI(
    title="Brief Bar scorer",
    version=scorer.version(),
    summary="Score a digital product brief against an open, versioned ruleset.",
    description=API_DESCRIPTION,
    openapi_tags=TAGS,
    contact={"name": "welance", "url": "https://briefs.welance.com", "email": "hello@welance.com"},
    license_info={"name": "MIT", "url": "https://github.com/welance/perfect-brief/blob/main/LICENSE"},
    lifespan=lifespan,
)

# Error shapes, documented once and attached to the calls that can raise them.
ErrDocs = dict[int | str, dict[str, Any]]
ERR_BRIEF: ErrDocs = {
    422: {"description": "The brief is empty, too long, or the `model` is not one this server allows."}
}
ERR_JUDGE: ErrDocs = {
    502: {"description": "The model upstream failed. Logged in full server-side; nothing partial is scored."},
    503: {
        "description": 'No model is configured (send `judge: "mock"` or your own key), or the model\'s answer was cut off before it finished.'
    },
}
ERR_RATE: ErrDocs = {
    429: {
        "description": "Too many calls from this address. Free calls and model-funded calls have separate limits."
    }
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


async def rate_limit(request: Request) -> None:
    bucket = request.headers.get("x-api-key") or (request.client.host if request.client else "anon")
    # Caller-controlled material never becomes part of a Redis key verbatim.
    bucket = hashlib.sha256(bucket.encode("utf-8", errors="replace")).hexdigest()
    if not await cache.allow(bucket):
        raise HTTPException(status_code=429, detail="rate limit exceeded — try again shortly")


async def paid_llm_rate_limit(request: Request, byok: str | None) -> None:
    """Protect the service-owned model account independently from free calls.

    An arbitrary X-API-Key is useful as a general quota label but is not
    authentication, so paid spend is always bucketed by the network client.
    BYOK calls spend the caller's provider account and skip this budget.
    """
    if byok:
        return
    client = request.client.host if request.client else "anon"
    bucket = "paid:" + hashlib.sha256(client.encode("utf-8", errors="replace")).hexdigest()
    if not await cache.allow(bucket, settings().paid_llm_rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="LLM rate limit exceeded — try again shortly")


def _guard(brief: str) -> None:
    if not brief.strip():
        raise HTTPException(status_code=422, detail="brief is empty")
    if len(brief) > settings().request_max_chars:
        raise HTTPException(status_code=413, detail=f"brief exceeds {settings().request_max_chars} chars")


def _guard_byok(key: str | None) -> None:
    if key is not None and len(key) > settings().byok_max_chars:
        raise HTTPException(status_code=400, detail="x-llm-key is too long")


# A caller-supplied OpenRouter key (bring your own key): used for that call
# only, never stored, never logged. It also unlocks any model (the caller pays).
ByokHeader = Annotated[
    str | None,
    Header(
        alias="x-llm-key",
        description="Optional. Your own OpenRouter key (`sk-or-…`). The call then runs on your "
        "account: no rate limit, no shared cache, and any model from the allowed list. Used for "
        "this one call, never stored, never logged. Use a spend-capped key.",
    ),
]


# Upstream failures are logged in full server-side and reported to the caller as
# a fixed string. Interpolating the exception would be more helpful and is how
# secrets escape: the caller's key is a header on the failing request, one
# unlucky exception type away from the response body. Safe by construction, not
# by which exception happens to arrive.
UPSTREAM_ERROR = "the judge upstream failed; the error was logged"
TRUNCATED_ERROR = (
    "the judge's answer was cut off before it finished, so no score was "
    "computed; retry, or raise PB_LLM_MAX_TOKENS"
)


def _judge_kind(requested: str | None, byok: str | None = None) -> str:
    kind = requested or settings().default_judge
    if kind == "llm" and not llm_client.configured() and not byok:
        raise HTTPException(status_code=503, detail="LLM judge not configured; use judge='mock'")
    return kind


# ---- API ------------------------------------------------------------------


@app.get("/v1/healthz", response_model=Health, tags=["meta"], summary="Is the service up, and with what?")
async def healthz() -> Health:
    """Always answers if the process is alive. Says which service release and which
    ruleset version are running, whether a model is configured for the live judge,
    and whether the verdict cache is connected. Safe to poll; never rate-limited."""
    return Health(
        release_version=SERVICE_VERSION,
        ruleset_version=scorer.version(),
        engine=scorer.engine(),
        llm_configured=llm_client.configured(),
        redis_connected=cache.connected(),
    )


@app.get(
    "/v1/models", response_model=ModelsResponse, tags=["meta"], summary="Which models may a request name?"
)
async def get_models() -> ModelsResponse:
    """The `model` field of a scoring request must be one of `available`, or the
    call is refused with 422. `default` is what runs when you name none. The list
    is the operator's allowlist, so a proxy cannot quietly pick an expensive model
    on the service's account. With your own key the list is wider (see `x-llm-key`)."""
    return ModelsResponse(
        default=llm_client.default_model(),
        available=llm_client.available_models(),
        llm_configured=llm_client.configured(),
    )


@app.get(
    "/v1/rules",
    response_model=RulesResponse,
    tags=["ruleset"],
    summary="The bar: all fourteen rules, weights and sources",
)
async def get_rules() -> RulesResponse:
    """Everything a verdict is measured against, in one document: each rule's
    title, rationale, criteria, weight, severity, whether it is a gate requirement,
    and the standards or practices it cites. Plus the accept threshold, the score
    bands and the budget floor. `ruleset_version` here is the one you will see on
    every verdict. Read this once and cache it; it changes only with a release."""
    cfg = scorer.cfg()
    rules = [
        RuleOut(
            id=r.id,
            title=r.title,
            rationale=r.rationale,
            weight=r.weight,
            severity=r.severity,
            gate=r.gate,
            criteria=r.criteria,
            references=[
                ReferenceOut(tier=x.tier, title=x.title, locator=x.locator, url=x.url) for x in r.references
            ],
        )
        for r in scorer.rules().values()
    ]
    return RulesResponse(
        ruleset_version=scorer.version(),
        accept=cfg.accept,
        budget_floor=cfg.budget_floor,
        gate=cfg.gate,
        bands=cfg.bands,
        rules=rules,
    )


@app.post(
    "/v1/score",
    response_model=ScoreResponse,
    tags=["score"],
    dependencies=[Depends(rate_limit)],
    summary="Score a brief: number, gate, and a verdict per rule",
    responses={**ERR_BRIEF, **ERR_JUDGE, **ERR_RATE},
)
async def post_score(req: ScoreRequest, request: Request, x_llm_key: ByokHeader = None) -> ScoreResponse:
    """Send the brief as plain text, in any language. You get back:

    - `score` (0–100) and its `band`, a human label;
    - `gate.passed` and `gate.missing`: fix these first, they block publication at
      any score;
    - `decision`: `accepted`, `accepted_with_reservation` or `blocked`, computed in
      code from gate and score, never by the model;
    - one verdict per rule with a verbatim `quote` from your brief as evidence.

    `judge: "mock"` scores on keywords with no model at all (English only).
    `judge: "llm"` uses the real judge; identical briefs on the same ruleset and
    model are answered from a one-day cache so nobody pays twice. Send
    `gate_contexts: []` to score a generic brief without the two rules that are
    noticeboard policy (anonymised, budget floor). Nothing you send is stored as a
    document; `no_cache: true` keeps even the evidence quotes out of the cache."""
    _guard_byok(x_llm_key)
    _guard(req.brief)
    kind = _judge_kind(req.judge, x_llm_key)
    if kind == "llm":
        await paid_llm_rate_limit(request, x_llm_key)
    try:
        return await scorer.score(
            req.brief,
            req.locale,
            kind,
            req.model,
            x_llm_key,
            gate_contexts=req.gate_contexts,
            no_cache=req.no_cache,
        )
    except ModelNotAllowed as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (JudgeTruncated, JudgeUnparsable) as exc:
        # Not the provider's fault and not a timeout: our ceiling. Say which,
        # and refuse rather than score a partial answer.
        log.warning("judge answer incomplete: %s", exc)
        raise HTTPException(status_code=503, detail=TRUNCATED_ERROR) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("scoring failed")
        raise HTTPException(status_code=502, detail=UPSTREAM_ERROR) from exc


def _screening_headers(response: Response, meta: dict) -> None:
    response.headers["X-PB-Screened"] = "true" if meta["screened"] else "false"
    response.headers["X-PB-Iterations"] = str(meta["iterations"])
    response.headers["X-PB-Verifier-Model"] = meta["verifier_model"] or "none"
    response.headers["X-PB-Generation-Ms"] = str(meta.get("generation_ms", 0))
    response.headers["X-PB-Verification-Ms"] = str(meta.get("verification_ms", 0))
    response.headers["X-PB-Cached"] = "true" if meta.get("cached") else "false"
    response.headers["X-PB-Cache-Ms"] = str(meta.get("cache_ms", 0))
    response.headers["X-PB-Model"] = meta.get("model") or "none"
    response.headers["Server-Timing"] = (
        f"cache;dur={meta.get('cache_ms', 0)}, "
        f"generation;dur={meta.get('generation_ms', 0)}, "
        f"verification;dur={meta.get('verification_ms', 0)}"
    )


@app.post(
    "/v1/suggest",
    response_model=list[Suggestion],
    tags=["fixes"],
    dependencies=[Depends(rate_limit)],
    summary="Sentences that would make one failing rule pass",
    responses={**ERR_BRIEF, **ERR_JUDGE, **ERR_RATE, 404: {"description": "No rule with that id."}},
)
async def post_suggest(
    req: SuggestRequest, request: Request, response: Response, x_llm_key: ByokHeader = None
) -> list[Suggestion]:
    """For one rule the brief fails, a short menu of ready-to-paste sentences,
    written to fit this brief and in the language you ask for. Each suggestion may
    carry a `review` from a second model that checked it against the rule; the
    `X-PB-*` response headers say whether that check ran, how many rounds it took
    and how long each step cost. Needs a model: the mock judge cannot write."""
    _guard_byok(x_llm_key)
    _guard(req.brief)
    if not llm_client.configured() and not x_llm_key:
        raise HTTPException(status_code=503, detail="suggestions require the LLM; not configured")
    await paid_llm_rate_limit(request, x_llm_key)
    try:
        suggestions, meta = await scorer.suggest(req.brief, req.rule_id, req.locale, req.model, x_llm_key)
        _screening_headers(response, meta)
        return suggestions
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown rule: {req.rule_id}") from None
    except ModelNotAllowed as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (JudgeTruncated, JudgeUnparsable) as exc:
        log.warning("suggestion answer incomplete: %s", exc)
        raise HTTPException(status_code=503, detail=TRUNCATED_ERROR) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("suggest failed")
        raise HTTPException(status_code=502, detail=UPSTREAM_ERROR) from exc


@app.post(
    "/v1/suggest/all",
    response_model=list[Suggestion],
    tags=["fixes"],
    dependencies=[Depends(rate_limit)],
    summary="One fix per failing rule, in a single call",
    responses={**ERR_BRIEF, **ERR_JUDGE, **ERR_RATE},
)
async def post_suggest_all(
    req: SuggestAllRequest, request: Request, response: Response, x_llm_key: ByokHeader = None
) -> list[Suggestion]:
    """The whole repair in one round trip: one suggestion for each rule id you pass
    (or for every rule that is not passing, if you pass none). Same shape and same
    `X-PB-*` headers as `/v1/suggest`. Insert the sentences, score again, repeat
    until `decision` is `accepted`. The anonymisation rule is the one thing it will
    not write for you: removing a client's name is a judgement, not a sentence."""
    _guard_byok(x_llm_key)
    _guard(req.brief)
    if not llm_client.configured() and not x_llm_key:
        raise HTTPException(status_code=503, detail="suggestions require the LLM; not configured")
    await paid_llm_rate_limit(request, x_llm_key)
    try:
        suggestions, meta = await scorer.suggest_all(
            req.brief, req.rule_ids, req.locale, req.model, x_llm_key
        )
        _screening_headers(response, meta)
        return suggestions
    except ModelNotAllowed as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (JudgeTruncated, JudgeUnparsable) as exc:
        log.warning("suggestion answer incomplete: %s", exc)
        raise HTTPException(status_code=503, detail=TRUNCATED_ERROR) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("suggest failed")
        raise HTTPException(status_code=502, detail=UPSTREAM_ERROR) from exc


# ---- the public pages (same files GitHub Pages serves) ---------------------

if SITE.exists():
    import re

    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    # A URL that changes when the bytes change is the only cache-busting that
    # nothing downstream can undo.
    #
    # 1.5.0 taught this the hard way. We versioned assets with `?v=N`, which a
    # CDN may cache ignoring the query string, and the release sat behind an
    # hour of stale JavaScript. Asking politely with `Cache-Control` is not
    # enough either: staging showed our `no-cache` rewritten to `max-age=14400`
    # before it reached the browser.
    #
    # So assets are served twice. `/chrome.js` stays exactly where it is, so
    # the same files still work unchanged on GitHub Pages, opened from disk, or
    # linked directly. Alongside it, `/a/<digest>/chrome.js` serves the same
    # bytes at an address derived from them, and the pages are rewritten on the
    # way out to point there. New bytes mean a new address, so caches never
    # have to be told anything: the old URL is simply no longer asked for.

    ASSET = re.compile(r'\b(href|src)="(?!https?:|//|/a/)([\w./-]+\.(?:css|js))"')

    def _digest() -> str:
        """One short digest over every asset."""
        h = hashlib.sha256()
        for path in sorted(SITE.rglob("*")):
            if path.suffix in {".css", ".js"}:
                h.update(path.relative_to(SITE).as_posix().encode())
                h.update(path.read_bytes())
        return h.hexdigest()[:12]

    BUILD = _digest()

    def _page(path: Path) -> str:
        """A page with its asset links pointed at the content-addressed copy."""
        return ASSET.sub(rf'\1="/a/{BUILD}/\2"', path.read_text(encoding="utf-8"))

    # The languages are declared once, in site/i18n.js, and read from there —
    # a second list here would be a second thing to keep true.
    def _langs() -> dict[str, str]:
        return dict(re.findall(r'code:\s*"([\w-]+)".*?dir:\s*"(\w+)"', (SITE / "i18n.js").read_text()))

    LANGS: dict[str, str] = _langs()

    def _localise(html: str, lang: str, page: str) -> str:
        """The same page, told which language it is being read in.

        English keeps the bare paths — it is the content of record, and moving
        it would move every URL that already exists. Every page names all of
        its translations, so a crawler finds them without following any script.
        """
        alt = "".join(
            f'<link rel="alternate" hreflang="{code}" href="/{"" if code == "en" else code + "/"}{page}">'
            for code in LANGS
        )
        alt += f'<link rel="alternate" hreflang="x-default" href="/{page}">'
        canonical = f'<link rel="canonical" href="/{"" if lang == "en" else lang + "/"}{page}">'
        html = html.replace("</head>", f"{alt}{canonical}</head>", 1)
        return re.sub(
            r'<html lang="[\w-]+" dir="\w+"',
            f'<html lang="{lang}" dir="{LANGS.get(lang, "ltr")}"',
            html,
            count=1,
        )

    def _pages() -> dict[str, str]:
        """Every page, once per language it can be read in."""
        out: dict[str, str] = {}
        for path in SITE.rglob("*.html"):
            name = path.relative_to(SITE).as_posix()
            html = _page(path)
            out[name] = _localise(html, "en", name)
            for lang in LANGS:
                if lang != "en":
                    out[f"{lang}/{name}"] = _localise(html, lang, name)
        return out

    PAGES = _pages()

    # In a container the files never change and this is read once. Locally they
    # change constantly, and a page served from a snapshot taken at startup is
    # a genuinely confusing thing to debug — you edit, reload, and see nothing.
    NEWEST = max((p.stat().st_mtime for p in SITE.rglob("*")), default=0.0)

    def _refresh_if_edited() -> None:
        global PAGES, BUILD, NEWEST, LANGS
        newest = max((p.stat().st_mtime for p in SITE.rglob("*")), default=0.0)
        if newest > NEWEST:
            # a new language is a new set of routes, so the list is re-read too
            NEWEST, BUILD, LANGS = newest, _digest(), _langs()
            PAGES = _pages()

    class Immutable(StaticFiles):
        """`/a/<digest>/welance.css` — this exact URL can never mean anything else.

        The digest is checked rather than routed on, so that when the files
        change under a running process the new digest simply starts working.
        """

        async def get_response(self, path: str, scope):  # type: ignore[override]
            digest, _, rest = path.lstrip("/").partition("/")
            if digest != BUILD or not rest:
                raise HTTPException(status_code=404, detail="not found")
            return await super().get_response(rest, scope)

        def file_response(self, *args, **kwargs):  # type: ignore[override]
            response = super().file_response(*args, **kwargs)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return response

    class Site(StaticFiles):
        """The pages, rewritten on the way out and never cached.

        A page is how a new build announces itself — it has to be fresh, and
        it is small. Anything else here (images, the ruleset, llms.txt) is
        served as it is, revalidated before it is reused.
        """

        async def get_response(self, path: str, scope):  # type: ignore[override]
            _refresh_if_edited()
            name = "index.html" if path in {"", ".", "/"} else path.lstrip("/")
            page = PAGES.get(name) or PAGES.get(f"{name.rstrip('/')}/index.html")
            if page is None and name.rstrip("/") in LANGS:
                page = PAGES.get(f"{name.rstrip('/')}/index.html")
            if page is not None:
                return HTMLResponse(page, headers={"Cache-Control": "no-cache"})
            return await super().get_response(path, scope)

        def file_response(self, *args, **kwargs):  # type: ignore[override]
            response = super().file_response(*args, **kwargs)
            response.headers["Cache-Control"] = "no-cache"
            return response

    # the hosted MCP connector: the same four tools as mcp-server/, for chats in
    # the browser that can add a remote server but cannot call the API themselves
    mcp_http.bind(
        rules=get_rules, health=healthz, score=post_score, suggest_all=post_suggest_all, free_limit=rate_limit
    )
    app.mount("/mcp", mcp_http.asgi_app(), name="mcp")
    app.mount("/a", Immutable(directory=str(SITE)), name="assets")
    app.mount("/", Site(directory=str(SITE), html=True), name="site")

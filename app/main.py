"""briefs.welance.com — the Perfect Brief scoring service.

Score is how good a brief is; a separate gate is whether it may publish. The
LLM only judges (server-side, key never leaves the box); code owns every number,
the gate, and the decision. The bundled console at / is the playground.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from . import cache, llm_client, scorer
from .llm_client import LLMNotConfigured, ModelNotAllowed
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

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("perfect_brief.api")

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
    yield
    await cache.close()


app = FastAPI(
    title="Perfect Brief scorer",
    version=scorer.version(),
    summary="Score a digital product brief against an open, versioned ruleset.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


async def rate_limit(request: Request) -> None:
    bucket = request.headers.get("x-api-key") or (request.client.host if request.client else "anon")
    if not await cache.allow(bucket):
        raise HTTPException(status_code=429, detail="rate limit exceeded — try again shortly")


def _guard(brief: str) -> None:
    if not brief.strip():
        raise HTTPException(status_code=422, detail="brief is empty")
    if len(brief) > settings().request_max_chars:
        raise HTTPException(status_code=413, detail=f"brief exceeds {settings().request_max_chars} chars")


# A caller-supplied OpenRouter key (bring your own key): used for that call
# only, never stored, never logged. It also unlocks any model (the caller pays).
ByokHeader = Annotated[
    str | None,
    Header(alias="x-llm-key", description="Optional: your own OpenRouter key for this call."),
]


def _judge_kind(requested: str | None, byok: str | None = None) -> str:
    kind = requested or settings().default_judge
    if kind == "llm" and not llm_client.configured() and not byok:
        raise HTTPException(status_code=503, detail="LLM judge not configured; use judge='mock'")
    return kind


# ---- API ------------------------------------------------------------------


@app.get("/v1/healthz", response_model=Health, tags=["meta"])
async def healthz() -> Health:
    return Health(
        ruleset_version=scorer.version(),
        engine=scorer.engine(),
        llm_configured=llm_client.configured(),
    )


@app.get("/v1/models", response_model=ModelsResponse, tags=["meta"])
async def get_models() -> ModelsResponse:
    return ModelsResponse(
        default=llm_client.default_model(),
        available=llm_client.available_models(),
        llm_configured=llm_client.configured(),
    )


@app.get("/v1/rules", response_model=RulesResponse, tags=["ruleset"])
async def get_rules() -> RulesResponse:
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


@app.post("/v1/score", response_model=ScoreResponse, tags=["score"], dependencies=[Depends(rate_limit)])
async def post_score(req: ScoreRequest, x_llm_key: ByokHeader = None) -> ScoreResponse:
    _guard(req.brief)
    kind = _judge_kind(req.judge, x_llm_key)
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
    except Exception as exc:  # noqa: BLE001
        log.exception("scoring failed")
        raise HTTPException(status_code=502, detail=f"judge error: {exc}") from exc


def _screening_headers(response: Response, meta: dict) -> None:
    response.headers["X-PB-Screened"] = "true" if meta["screened"] else "false"
    response.headers["X-PB-Iterations"] = str(meta["iterations"])
    response.headers["X-PB-Verifier-Model"] = meta["verifier_model"] or "none"


@app.post("/v1/suggest", response_model=list[Suggestion], tags=["fixes"], dependencies=[Depends(rate_limit)])
async def post_suggest(
    req: SuggestRequest, response: Response, x_llm_key: ByokHeader = None
) -> list[Suggestion]:
    _guard(req.brief)
    if not llm_client.configured() and not x_llm_key:
        raise HTTPException(status_code=503, detail="suggestions require the LLM; not configured")
    try:
        suggestions, meta = await scorer.suggest(req.brief, req.rule_id, req.locale, req.model, x_llm_key)
        _screening_headers(response, meta)
        return suggestions
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown rule: {req.rule_id}") from None
    except ModelNotAllowed as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"suggest error: {exc}") from exc


@app.post(
    "/v1/suggest/all", response_model=list[Suggestion], tags=["fixes"], dependencies=[Depends(rate_limit)]
)
async def post_suggest_all(
    req: SuggestAllRequest, response: Response, x_llm_key: ByokHeader = None
) -> list[Suggestion]:
    _guard(req.brief)
    if not llm_client.configured() and not x_llm_key:
        raise HTTPException(status_code=503, detail="suggestions require the LLM; not configured")
    try:
        suggestions, meta = await scorer.suggest_all(
            req.brief, req.rule_ids, req.locale, req.model, x_llm_key
        )
        _screening_headers(response, meta)
        return suggestions
    except ModelNotAllowed as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"suggest error: {exc}") from exc


# ---- the public pages (same files GitHub Pages serves) ---------------------

if SITE.exists():
    import hashlib
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
        """One short digest over every asset, recomputed at startup only."""
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

    PAGES = {p.relative_to(SITE).as_posix(): _page(p) for p in SITE.rglob("*.html")}

    class Immutable(StaticFiles):
        """Content-addressed: this exact URL can never mean anything else."""

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
            name = "index.html" if path in {"", ".", "/"} else path.lstrip("/")
            page = PAGES.get(name) or PAGES.get(f"{name.rstrip('/')}/index.html")
            if page is not None:
                return HTMLResponse(page, headers={"Cache-Control": "no-cache"})
            return await super().get_response(path, scope)

        def file_response(self, *args, **kwargs):  # type: ignore[override]
            response = super().file_response(*args, **kwargs)
            response.headers["Cache-Control"] = "no-cache"
            return response

    app.mount(f"/a/{BUILD}", Immutable(directory=str(SITE)), name="assets")
    app.mount("/", Site(directory=str(SITE), html=True), name="site")

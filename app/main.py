"""briefs.welance.com — the Perfect Brief scoring service.

Score is how good a brief is; a separate gate is whether it may publish. The
LLM only judges (server-side, key never leaves the box); code owns every number,
the gate, and the decision. The bundled console at / is the playground.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import anthropic_client, cache, scorer
from .anthropic_client import LLMNotConfigured
from .models import (
    Health,
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

STATIC = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    log.info(
        "ruleset %s · %d rules · LLM configured: %s",
        scorer.version(),
        len(scorer.rules()),
        anthropic_client.configured(),
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


def _judge_kind(requested: str | None) -> str:
    kind = requested or settings().default_judge
    if kind == "llm" and not anthropic_client.configured():
        raise HTTPException(status_code=503, detail="LLM judge not configured; use judge='mock'")
    return kind


# ---- API ------------------------------------------------------------------


@app.get("/v1/healthz", response_model=Health, tags=["meta"])
async def healthz() -> Health:
    return Health(
        ruleset_version=scorer.version(),
        engine=scorer.engine(),
        llm_configured=anthropic_client.configured(),
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
async def post_score(req: ScoreRequest) -> ScoreResponse:
    _guard(req.brief)
    kind = _judge_kind(req.judge)
    try:
        return await scorer.score(req.brief, req.locale, kind)
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("scoring failed")
        raise HTTPException(status_code=502, detail=f"judge error: {exc}") from exc


@app.post("/v1/suggest", response_model=list[Suggestion], tags=["fixes"], dependencies=[Depends(rate_limit)])
async def post_suggest(req: SuggestRequest) -> list[Suggestion]:
    _guard(req.brief)
    if not anthropic_client.configured():
        raise HTTPException(status_code=503, detail="suggestions require the LLM; not configured")
    try:
        return await scorer.suggest(req.brief, req.rule_id, req.locale)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown rule: {req.rule_id}") from None
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"suggest error: {exc}") from exc


@app.post(
    "/v1/suggest/all", response_model=list[Suggestion], tags=["fixes"], dependencies=[Depends(rate_limit)]
)
async def post_suggest_all(req: SuggestAllRequest) -> list[Suggestion]:
    _guard(req.brief)
    if not anthropic_client.configured():
        raise HTTPException(status_code=503, detail="suggestions require the LLM; not configured")
    try:
        return await scorer.suggest_all(req.brief, req.rule_ids, req.locale)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"suggest error: {exc}") from exc


# ---- static console (the playground) --------------------------------------


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


if STATIC.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")

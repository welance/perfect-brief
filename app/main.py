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


# Upstream failures are logged in full server-side and reported to the caller as
# a fixed string. Interpolating the exception would be more helpful and is how
# secrets escape: the caller's key is a header on the failing request, one
# unlucky exception type away from the response body. Safe by construction, not
# by which exception happens to arrive.
UPSTREAM_ERROR = "the judge upstream failed; the error was logged"


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
        raise HTTPException(status_code=502, detail=UPSTREAM_ERROR) from exc


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
        log.exception("suggest failed")
        raise HTTPException(status_code=502, detail=UPSTREAM_ERROR) from exc


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
        log.exception("suggest failed")
        raise HTTPException(status_code=502, detail=UPSTREAM_ERROR) from exc


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

    app.mount("/a", Immutable(directory=str(SITE)), name="assets")
    app.mount("/", Site(directory=str(SITE), html=True), name="site")

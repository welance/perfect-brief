"""Resolve the ruleset data bundled with the package, and version it.

The ruleset is package data (rules/*.yaml + scoring.yaml). It is loaded once and
versioned by a content digest so every score can be pinned and reproduced: same
digest + same verdicts -> same number, forever.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parent


def rules_dir() -> str:
    return str(_DATA / "rules")


def scoring_path() -> str:
    return str(_DATA / "scoring.yaml")


def fixtures_dir() -> str:
    return str(_DATA / "fixtures")


def schemas_dir() -> str:
    return str(_DATA / "schemas")


@lru_cache(maxsize=1)
def semver() -> str:
    return (_DATA / "VERSION").read_text().strip()


@lru_cache(maxsize=1)
def content_digest() -> str:
    """A short, stable hash of every rule file + scoring.yaml."""
    h = hashlib.sha256()
    for p in sorted((_DATA / "rules").glob("*.yaml")) + [_DATA / "scoring.yaml"]:
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


@lru_cache(maxsize=1)
def ruleset_version() -> str:
    """e.g. '1.0.0+ab12cd34ef56' — semver for humans, digest for reproducibility."""
    return f"{semver()}+{content_digest()}"

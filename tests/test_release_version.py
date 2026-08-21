"""One release number across every artifact a human or tool can publish."""

import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_release_versions_are_in_sync():
    service = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    mcp = tomllib.loads((ROOT / "mcp-server/pyproject.toml").read_text())["project"]["version"]
    runtime_match = re.search(
        r'^SERVICE_VERSION = "([^"]+)"$',
        (ROOT / "app/version.py").read_text(),
        re.MULTILINE,
    )
    compose = (ROOT / "docker-compose.yml").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()
    chrome = (ROOT / "site/chrome.js").read_text()

    assert mcp == service
    assert runtime_match and runtime_match.group(1) == service
    assert re.search(rf"image: welance/perfect-brief:{re.escape(service)}$", compose, re.MULTILINE)
    assert f"## [{service}]" in changelog
    assert 'fetch("/v1/healthz"' in chrome
    assert "© 2011–2026 · v1 · live" not in chrome

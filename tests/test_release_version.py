"""One release number across every artifact a human or tool can publish."""

import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_release_versions_are_in_sync():
    service = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    mcp = tomllib.loads((ROOT / "mcp-server/pyproject.toml").read_text())["project"]["version"]
    compose = (ROOT / "docker-compose.yml").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()

    assert mcp == service
    assert re.search(rf"image: welance/perfect-brief:{re.escape(service)}$", compose, re.MULTILINE)
    assert f"## [{service}]" in changelog

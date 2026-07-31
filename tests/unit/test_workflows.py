"""Release workflow contract tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[2]


def _workflow(name: str) -> tuple[dict[str, Any], str]:
    text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    parsed = yaml.load(text, Loader=yaml.BaseLoader)
    assert isinstance(parsed, dict)
    return parsed, text


def test_successful_main_ci_creates_release_and_dispatches_publish() -> None:
    workflow, text = _workflow("auto-release.yml")
    trigger = workflow["on"]["workflow_run"]
    assert trigger["workflows"] == ["CI"]
    assert trigger["branches"] == ["main"]
    assert trigger["types"] == ["completed"]
    assert workflow["permissions"] == {"actions": "write", "contents": "write"}
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "gh release create" in text
    assert "gh workflow run release.yml" in text
    assert '--field tag="$TAG_NAME"' in text


def test_publish_accepts_release_event_and_explicit_dispatch_tag() -> None:
    workflow, text = _workflow("release.yml")
    assert workflow["on"]["release"]["types"] == ["published"]
    tag_input = workflow["on"]["workflow_dispatch"]["inputs"]["tag"]
    assert tag_input["required"] == "true"
    assert tag_input["type"] == "string"
    assert "github.event.release.tag_name || inputs.tag" in text
    assert "pypa/gh-action-pypi-publish@release/v1" in text


def test_docs_builds_on_pull_requests_and_deploys_main_with_scoped_permissions() -> None:
    workflow, text = _workflow("docs.yml")
    assert "pull_request" in workflow["on"]
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert workflow["jobs"]["build"]["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["deploy"]["permissions"] == {
        "pages": "write",
        "id-token": "write",
    }
    assert "mkdocs build --strict" in text
    assert "actions/upload-pages-artifact@v4" in text
    assert "actions/deploy-pages@v4" in text

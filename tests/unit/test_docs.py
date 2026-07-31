"""Documentation-site configuration and discoverability contract tests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[2]
DOCS = ROOT / "docs"


def test_mkdocs_uses_public_canonical_site_and_required_navigation() -> None:
    config = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    assert config["site_url"] == "https://flavvesresearch.github.io/opencv-calibration-audit/"
    assert config["repo_url"] == "https://github.com/flavvesResearch/opencv-calibration-audit"
    serialized_nav = json.dumps(config["nav"])
    for required in (
        "index.md",
        "guide/validate-opencv-camera-calibration-dataset.md",
        "reference/cli.md",
        "reference/python-api.md",
        "reference/output-schema.md",
        "reference/decision-codes.md",
        "examples/small-real-image-smoke-example.md",
        "examples/production-dataset-benchmark.md",
    ):
        assert required in serialized_nav


def test_documentation_pages_have_unique_descriptions() -> None:
    descriptions: list[str] = []
    for page in sorted(DOCS.rglob("*.md")):
        text = page.read_text(encoding="utf-8")
        assert text.startswith("---\n"), page
        _, frontmatter, _ = text.split("---", maxsplit=2)
        metadata = yaml.safe_load(frontmatter)
        assert metadata["title"], page
        descriptions.append(metadata["description"])
    assert len(descriptions) == len(set(descriptions))


def test_homepage_structured_data_is_truthful_and_parseable() -> None:
    home = (DOCS / "index.md").read_text(encoding="utf-8")
    match = re.search(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        home,
        flags=re.DOTALL,
    )
    assert match is not None
    payload: dict[str, Any] = json.loads(match.group(1))
    assert payload["@type"] == "SoftwareApplication"
    assert payload["softwareVersion"] == "0.2.2"
    assert payload["offers"]["price"] == "0"
    assert "aggregateRating" not in payload


def test_readme_uses_absolute_published_report_links_and_smoke_label() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    site = "https://flavvesresearch.github.io/opencv-calibration-audit/"
    assert f"{site}images/report-v0.2.1.svg" in readme
    assert f"{site}example-report/report.html" in readme
    assert f"{site}example-report/summary.json" in readme
    rendered_text = readme.replace("\n> ", " ")
    assert re.search(
        r"not a production-ready calibration\s+dataset",
        rendered_text,
        flags=re.IGNORECASE,
    )

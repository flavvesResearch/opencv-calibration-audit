# Contributing

Create a focused branch and install the development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Before proposing a change, run:

```bash
ruff check .
mypy .
pytest --cov=calibration_audit --cov-report=term-missing
python -m build
twine check dist/*
```

New metrics should keep measurement separate from policy, include typed public
results, and have tests for normal, boundary, and failure cases. Never modify
calibration input images in place.

## Release policy

Ordinary pushes and merges never create a tag, GitHub Release, or PyPI
publication. After the complete CI workflow passes, a maintainer may explicitly
publish a GitHub Release whose tag exactly matches the version in
`pyproject.toml` (for example, `v0.2.1`). Publishing that release triggers the
Trusted Publishing workflow. Release notes should summarize the corresponding
grouped entries in `CHANGELOG.md`.

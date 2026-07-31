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

A version change merged to `main` authorizes a release. After the complete
`main` CI workflow passes, `auto-release.yml` reads the version from
`pyproject.toml` and creates the matching tag and GitHub Release when it does
not already exist. It explicitly dispatches the PyPI Trusted Publishing workflow
in `release.yml`; manually published Releases trigger the same workflow through
the `release` event. Commits that keep an already released version are safely
skipped. For recovery, `release.yml` can be manually dispatched with an existing
release tag. Release notes should summarize the corresponding grouped entries
in `CHANGELOG.md`.

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

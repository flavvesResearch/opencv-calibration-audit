# OpenCV Camera Calibration Dataset Audit

[![PyPI Version](https://img.shields.io/pypi/v/opencv-calibration-audit?label=PyPI&cacheSeconds=300)](https://pypi.org/project/opencv-calibration-audit/)
[![Python Versions](https://img.shields.io/pypi/pyversions/opencv-calibration-audit?cacheSeconds=300)](https://pypi.org/project/opencv-calibration-audit/)
[![License](https://img.shields.io/pypi/l/opencv-calibration-audit?cacheSeconds=300)](https://github.com/flavvesResearch/opencv-calibration-audit/blob/main/LICENSE)

Validate checkerboard image datasets before `cv2.calibrateCamera`. Detect blur,
exposure problems, duplicate poses, weak image-plane coverage, limited pose
diversity, and high reprojection error, then generate an explainable offline
report.

The tool records why each image was accepted, warned, rejected, or unreadable
and exports human-readable and machine-readable evidence. Analysis runs locally
without telemetry or network requests and never modifies source images.

[Read the documentation](https://flavvesresearch.github.io/opencv-calibration-audit/) ·
[Install from PyPI](https://pypi.org/project/opencv-calibration-audit/) ·
[View the main validation guide](https://flavvesresearch.github.io/opencv-calibration-audit/guide/validate-opencv-camera-calibration-dataset/)

## Installation

```bash
python -m pip install opencv-calibration-audit
```

Python 3.10–3.13 is supported. The package uses headless OpenCV and tests both
OpenCV 4.11 and 5.x.

## 30-second quick start

```bash
calibration-audit analyze ./calibration_images \
  --cols 9 \
  --rows 6 \
  --square-size 30 \
  --unit mm \
  --output ./audit_result
```

`--cols` and `--rows` count inner corners, not squares. A checkerboard with
10 × 7 squares has 9 × 6 inner corners.

```text
Quality gates: PASSED
Accepted views: 12
OpenCV RMS: 0.284931 px
Report: audit_result/report.html
```

The command refuses a non-empty output directory unless
`--overwrite-output` is supplied. See the
[CLI reference](https://flavvesresearch.github.io/opencv-calibration-audit/reference/cli/)
for thresholds, recursion, quality gates, and exit codes.

## Example report

The published report uses three redistributable real-camera images from
OpenCV's sample data.

> **Small real-image smoke example — not a production-ready calibration
> dataset.** Its coverage ratio is `0.0833`, it contains two image warnings,
> and the checked-in run gates only the minimum valid-image count.

![Annotated checkerboard decisions in the small real-image smoke report](https://flavvesresearch.github.io/opencv-calibration-audit/images/report-v0.2.1.svg)

[Open the self-contained example report](https://flavvesresearch.github.io/opencv-calibration-audit/example-report/report.html) or
[inspect its `summary.json`](https://flavvesresearch.github.io/opencv-calibration-audit/example-report/summary.json).
The [reproduction guide](https://flavvesresearch.github.io/opencv-calibration-audit/examples/small-real-image-smoke-example/)
includes source, license, exact commands, measurements, and an intentional
`--fail-on-warning` run.

## What it measures

- Complete checkerboard detection and readable-image rate.
- Global and board-region sharpness plus exposure warnings.
- Physical board area, border safety, image-plane coverage, and corner density.
- Scale bins, circular rotation range, and signed perspective diversity.
- Near-duplicate pose using normalized position, area, rotation, and
  perspective.
- OpenCV pinhole RMS and per-view reprojection statistics.

Coverage, diversity, sharpness, and duplicate thresholds are heuristics, not a
calibration certificate. Per-view reprojection error is in-sample because the
same accepted images fit and evaluate the model.

[Learn how the metrics work](https://flavvesresearch.github.io/opencv-calibration-audit/concepts/coverage-and-diversity/) ·
[Review decision codes](https://flavvesresearch.github.io/opencv-calibration-audit/reference/decision-codes/)

## Output

```text
audit_result/
├── report.html
├── summary.json
├── images.csv
├── calibration.yaml
├── accepted.txt
├── rejected.txt
├── report-manifest.json
└── assets/
    ├── coverage_heatmap.png
    ├── reprojection_errors.png
    └── thumbnails/
```

`report.html` is self-contained and works offline. `summary.json` contains
typed reason codes, runtime versions, configuration, dataset metrics, quality
gates, calibration parameters, and per-image results.

[Read the complete output schema](https://flavvesresearch.github.io/opencv-calibration-audit/reference/output-schema/).

## Python API

```python
from pathlib import Path

from calibration_audit import AuditConfig, PatternSpec, audit_dataset

config = AuditConfig(
    pattern=PatternSpec(cols=9, rows=6, square_size=30.0, unit="mm"),
    min_valid_images=12,
)
result = audit_dataset(Path("./calibration_images"), config)

print(result.summary)
result.write_outputs(Path("./audit_result"))
```

Library functions raise typed `CalibrationAuditError` subclasses and never
call `sys.exit()`. See the
[Python API reference](https://flavvesresearch.github.io/opencv-calibration-audit/reference/python-api/).

## Limitations

Version 0.2.2 supports standard black-and-white checkerboards, monocular
calibration, and the pinhole camera model. It does not support stereo or
fisheye calibration, ChArUco/ArUco, circle grids, live capture, ROS output, a
GUI, automatic view pruning, or input-file modification.

[Read the full scope and limitations](https://flavvesresearch.github.io/opencv-calibration-audit/about/limitations/).

## Development

```bash
python -m pip install -e ".[dev,docs]"
ruff check .
mypy .
pytest --cov=calibration_audit --cov-report=term-missing --cov-fail-under=85
python -m build
twine check dist/*
mkdocs build --strict
```

CI tests Python 3.10–3.13, OpenCV 4.11/5.x, and Windows/macOS smoke
installations. Documentation has a separate pull-request build and GitHub Pages
deployment workflow.

## License

MIT. See [LICENSE](https://github.com/flavvesResearch/opencv-calibration-audit/blob/main/LICENSE).

# OpenCV Calibration Audit

[![PyPI Version](https://img.shields.io/pypi/v/opencv-calibration-audit?label=PyPI&cacheSeconds=300)](https://pypi.org/project/opencv-calibration-audit/)
[![Python Versions](https://img.shields.io/pypi/pyversions/opencv-calibration-audit?cacheSeconds=300)](https://pypi.org/project/opencv-calibration-audit/)
[![License](https://img.shields.io/pypi/l/opencv-calibration-audit?cacheSeconds=300)](LICENSE)

Audit OpenCV checkerboard calibration datasets, reject weak or duplicate views,
visualize image-plane coverage, calibrate a monocular pinhole camera, and create
an explainable offline report.

Unlike a short `cv2.calibrateCamera()` script, this package inspects the input
dataset first. It records why each image was accepted, warned, rejected, or
unreadable and exports both human-readable and machine-readable evidence.
Analysis is local and contains no telemetry or network requests.

## Installation

```bash
python -m pip install opencv-calibration-audit
```

Python 3.9–3.13 is supported. The implementation uses
`findChessboardCornersSB`. CI explicitly tests OpenCV 4.11.0.86 and the latest
OpenCV 5.x release; the default dependency is the headless OpenCV wheel.
Version `0.2.0` was the first functional audit MVP. Earlier `0.1.x` packages
were development scaffolds and should not be installed.

## Five-minute quick start

```bash
calibration-audit analyze ./calibration_images \
  --cols 9 \
  --rows 6 \
  --square-size 30 \
  --unit mm \
  --output ./audit_result
```

`--cols` and `--rows` always mean **inner corners**, not squares. A target with
10 × 7 squares has 9 × 6 inner corners.

Example terminal summary:

```text
Quality gates: PASSED
Accepted views: 12
OpenCV RMS: 0.284931 px
Report: audit_result/report.html
```

Useful stricter options:

```bash
calibration-audit analyze ./calibration_images \
  --cols 9 --rows 6 --square-size 30 --unit mm \
  --recursive \
  --min-valid-images 12 \
  --min-board-area 0.05 \
  --max-per-view-error 1.0 \
  --fail-on-warning \
  --output ./audit_result
```

The command will not overwrite a non-empty output directory unless
`--overwrite-output` is supplied.

## Example report

This report was generated from the three redistributable real-camera OpenCV
fixtures included with the test suite:

```bash
calibration-audit analyze ./real_checkerboards \
  --cols 9 --rows 6 --square-size 30 --unit mm \
  --min-valid-images 3 --min-board-area 0.01 \
  --output ./audit_result
```

```text
Quality gates: PASSED
Accepted views: 3
OpenCV RMS: 0.203403 px
Report: audit_result/report.html
```

![Annotated per-image decisions in the v0.2.1 report](docs/images/report-v0.2.1.svg)

[Open the self-contained example report](docs/example-report/report.html) or
[inspect its `summary.json`](docs/example-report/summary.json).

## Python API

```python
from pathlib import Path

from calibration_audit import AuditConfig, PatternSpec, audit_dataset

config = AuditConfig(
    pattern=PatternSpec(
        cols=9,
        rows=6,
        square_size=30.0,
        unit="mm",
    ),
    min_valid_images=12,
)

result = audit_dataset(
    image_directory=Path("./calibration_images"),
    config=config,
)

print(result.summary)
result.write_outputs(Path("./audit_result"))
```

Library functions raise typed `CalibrationAuditError` subclasses and never
call `sys.exit()`.

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

`report.html` embeds its charts, CSS, and annotated per-image previews and works
offline without a CDN. Filenames and decision messages are escaped. Each image
shows the decision stage, reason severity, message, measured value, and
threshold or rule. `summary.json` contains typed reason codes, the OpenCV
runtime version, configuration, dataset metrics, quality gates, calibration
parameters, and per-image results. `report-manifest.json` identifies
generator-owned files so overwrite removes stale assets without touching
unrelated files. `calibration.yaml` uses an OpenCV-friendly matrix layout; it
does not claim ROS camera-info compatibility.

## What is measured

- Detection rate: complete detections divided by readable images.
- Sharpness: variance of Laplacian globally and inside the detected board.
  With no user threshold, only clear dataset-relative outliers are warned.
- Exposure: mean grayscale intensity and near-black/near-white ratios.
- Board geometry: normalized center, physical target area, rotation, signed
  perspective imbalance, and physical-boundary border distance. The physical
  boundary is estimated one square beyond the outer detected inner corners.
  The sharpness ROI remains the conservative inner-corner hull.
- Coverage: occupied board-center cells in a 4 × 3 image-plane grid plus
  corner-observation density.
- Diversity: board-area distribution, occupied scale bins, smallest circular
  rotation range, and horizontal/vertical perspective ranges. For example,
  `179°` and `-179°` span approximately `2°`; the four cardinal orientations
  span a smallest covering arc of `270°`.
- Duplicate pose: normalized position, log-area, rotation, and perspective
  thresholds. The sharper of two near-identical views is kept.
- Calibration: OpenCV pinhole RMS, camera matrix, distortion coefficients,
  extrinsics, and per-view reprojection statistics.

Per-view reprojection RMSE is:

```text
sqrt(mean((projected_x - observed_x)^2 + (projected_y - observed_y)^2))
```

Horizontal perspective is `(top - bottom) / max(top, bottom)` and vertical
perspective is `(left - right) / max(left, right)`, so their signs retain tilt
direction. The coverage and diversity assessments are heuristics, not a
calibration certificate. Sharpness values are especially dependent on
resolution, target scale, focus, and lens characteristics.

The default near-duplicate component thresholds are: normalized center
distance `0.03`, absolute log-area distance `0.08`, wrapped rotation distance
`5°`, and combined perspective distance `0.08`. These are typed policy values
in the Python API. The default relative-sharpness warning threshold is
`0.35 ×` the dataset median.

## Decisions and exit codes

Every rejection includes a stable reason code, severity, message, measured
value, and relevant threshold. High reprojection-error views are flagged after
the initial calibration and are not silently removed or recalibrated.
Per-view reprojection error is in-sample: it is computed after fitting on the
same accepted images and is not independent validation.

| Code | Meaning |
| ---: | --- |
| 0 | Audit completed and quality gates passed |
| 1 | Audit completed but a configured quality gate failed |
| 2 | Invalid arguments or invalid input dataset |
| 3 | Unexpected processing/calibration failure |

Tracebacks are hidden by default and shown only with `--log-level DEBUG`.

## Input behavior

Supported formats are JPEG, PNG, BMP, TIFF, and WebP. Unsigned 8-bit inputs are
analyzed directly. Unsigned 16-bit inputs, including TIFF, use the fixed mapping
`value / 257` to 8-bit analysis pixels; per-image min/max stretching is not
used. Original dtype and bit depth remain in per-image metrics. Signed and
floating-point images are rejected as unsupported.

Files are processed in deterministic sorted order. Unreadable images are
reported individually. Mixed readable resolutions fail clearly and list their
resolution groups. Source images are never deleted, moved, rewritten, or
otherwise modified. Recursive discovery ignores symlinks that resolve outside
the requested input tree and rejects any output path that resolves inside the
input tree, preventing an earlier report from becoming calibration input.

## Limitations

The MVP supports standard black-and-white checkerboards, monocular calibration,
and the pinhole camera model. It does not support stereo or fisheye
calibration, ChArUco/ArUco, circle grids, live capture, ROS output, a GUI, PDF
reports, automatic view pruning, or input-file modification.

To generate a print-accurate target, use the companion
[`opencv-chessboard-generator`](https://pypi.org/project/opencv-chessboard-generator/).

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy .
pytest --cov=calibration_audit --cov-report=term-missing
python -m build
twine check dist/*
```

CI tests Python 3.9–3.13 plus explicit OpenCV 4.11 and 5.x jobs. Ordinary
pushes and merges do not publish. After CI succeeds, a maintainer must
explicitly publish a GitHub Release whose tag matches the version in
`pyproject.toml`; that release triggers the separate PyPI Trusted Publishing
workflow.

## License

MIT. See [LICENSE](LICENSE).

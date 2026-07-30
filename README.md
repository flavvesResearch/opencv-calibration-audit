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
`findChessboardCornersSB`, available in supported OpenCV 4.x releases and
OpenCV 5.x. The default dependency is the headless OpenCV wheel.

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
└── assets/
    ├── coverage_heatmap.png
    ├── reprojection_errors.png
    └── thumbnails/
```

`report.html` embeds its charts, CSS, and data images and works offline without
a CDN. Filenames are escaped. `summary.json` contains typed reason codes,
configuration, dataset metrics, quality gates, calibration parameters, and
per-image results. `calibration.yaml` uses an OpenCV-friendly matrix layout;
it does not claim ROS camera-info compatibility.

## What is measured

- Detection rate: complete detections divided by readable images.
- Sharpness: variance of Laplacian globally and inside the detected board.
  With no user threshold, only clear dataset-relative outliers are warned.
- Exposure: mean grayscale intensity and near-black/near-white ratios.
- Board geometry: normalized center, area, rotation, perspective imbalance,
  and border distance.
- Coverage: occupied board-center cells in a 4 × 3 image-plane grid plus
  corner-observation density.
- Diversity: board-area distribution, occupied scale bins, rotation range,
  and horizontal/vertical perspective ranges.
- Duplicate pose: normalized position, log-area, rotation, and perspective
  thresholds. The sharper of two near-identical views is kept.
- Calibration: OpenCV pinhole RMS, camera matrix, distortion coefficients,
  extrinsics, and per-view reprojection statistics.

Per-view reprojection RMSE is:

```text
sqrt(mean((projected_x - observed_x)^2 + (projected_y - observed_y)^2))
```

The coverage and diversity assessments are heuristics, not physical
measurements or a calibration certificate. Sharpness values are especially
dependent on resolution, target scale, focus, and lens characteristics.

The default near-duplicate component thresholds are: normalized center
distance `0.03`, absolute log-area distance `0.08`, wrapped rotation distance
`5°`, and combined perspective distance `0.08`. These are typed policy values
in the Python API. The default relative-sharpness warning threshold is
`0.35 ×` the dataset median.

## Decisions and exit codes

Every rejection includes a stable reason code, severity, message, measured
value, and relevant threshold. High reprojection-error views are flagged after
the initial calibration and are not silently removed or recalibrated.

| Code | Meaning |
| ---: | --- |
| 0 | Audit completed and quality gates passed |
| 1 | Audit completed but a configured quality gate failed |
| 2 | Invalid arguments or invalid input dataset |
| 3 | Unexpected processing/calibration failure |

Tracebacks are hidden by default and shown only with `--log-level DEBUG`.

## Input behavior

Supported formats are JPEG, PNG, BMP, TIFF, and WebP. Files are processed in a
deterministic sorted order. Unreadable images are reported individually.
Mixed readable resolutions fail clearly and list their resolution groups.
Source images are never deleted, moved, rewritten, or otherwise modified.
Recursive discovery ignores symlinks that resolve outside the requested input
tree.

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

CI tests Python 3.9–3.13. Publishing is deliberately separate from ordinary CI
and can run only for an explicitly published GitHub Release whose tag matches
the project version.

## License

MIT. See [LICENSE](LICENSE).

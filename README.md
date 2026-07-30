# OpenCV Calibration Audit

[![PyPI Version](https://img.shields.io/pypi/v/opencv-calibration-audit.svg)](https://pypi.org/project/opencv-calibration-audit/)
[![Python Versions](https://img.shields.io/pypi/pyversions/opencv-calibration-audit.svg)](https://pypi.org/project/opencv-calibration-audit/)
[![License](https://img.shields.io/pypi/l/opencv-calibration-audit.svg)](https://github.com/your-username/opencv-calibration-audit/blob/main/LICENSE)

**Audit OpenCV checkerboard calibration datasets, detect weak or duplicate views, visualize image-plane coverage, calibrate the camera, and generate an explainable offline report.**

This package provides a production-quality, installable tool to inspect and validate checkerboard image datasets used for monocular camera calibration with OpenCV. It's designed to be a reliable quality gate in computer vision and robotics pipelines.

The main differentiator of this tool is its focus on dataset quality analysis, explainable rejection reasons for bad images, and comprehensive reporting, rather than just being a minimal wrapper around `cv2.calibrateCamera()`.

This project is intended to complement the [`opencv-chessboard-generator`](https://pypi.org/project/opencv-chessboard-generator/) package.

## Key Features

- **Dataset Validation**: Checks for consistent image resolutions, sufficient image counts, and readable files.
- **Checkerboard Detection**: Uses `cv2.findChessboardCornersSB` for robust corner detection.
- **Image Quality Metrics**: Measures sharpness, board geometry, exposure, and perspective.
- **Dataset-Level Analysis**: Analyzes field-of-view coverage, pose diversity (scale, orientation), and detects near-duplicate images.
- **Camera Calibration**: Performs a standard pinhole camera calibration.
- **Explainable Results**: Provides clear, structured reason codes for every rejected or flagged image.
- **Rich Reporting**: Exports results to JSON, YAML, CSV, and a self-contained HTML report.
- **CLI and Python API**: Usable as both a command-line tool and a Python library.

## Installation

```bash
pip install opencv-calibration-audit
```

## Quick Start

Run an audit on a directory of calibration images with the following command:

```bash
calibration-audit analyze ./calibration_images \
  --cols 9 \
  --rows 6 \
  --square-size 30 \
  --unit mm \
  --output ./audit_result
```

### Important Convention: Inner Corners

The `--cols` and `--rows` arguments **always refer to the number of inner corners** on the checkerboard, not the number of squares.

For a 10x7 checkerboard (10 squares by 7 squares), the number of inner corners is 9x6.

```
+---+---+---+---+
| ● | ● | ● | ● |  <-- 4x3 inner corners
+---+---+---+---+
| ● | ● | ● | ● |
+---+---+---+---+
| ● | ● | ● | ● |
+---+---+---+---+
```

## Python API Usage

```python
from pathlib import Path

from calibration_audit import AuditConfig, PatternSpec, audit_dataset

# This is a future-state example; audit_dataset is not yet implemented in Phase 1
# config = AuditConfig(
#     pattern=PatternSpec(
#         cols=9,
#         rows=6,
#         square_size=30.0,
#         unit="mm",
#     ),
#     min_valid_images=12,
# )

# result = audit_dataset(
#     image_directory=Path("./calibration_images"),
#     config=config,
# )

# print(result.summary)
# result.write_outputs(Path("./audit_result"))
```

## Limitations (MVP)

The initial version focuses on monocular, pinhole camera calibration with standard checkerboards. The following are explicitly excluded from the MVP:

- Stereo, fisheye, or multi-camera calibration
- ChArUco, ArUco, or circle-grid targets
- Live camera capture or GUI interfaces

## Development

To set up a development environment:

```bash
# Clone the repository
git clone https://example.com/your-repo.git
cd opencv-calibration-audit

# Install in editable mode with dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Run linters and type checkers
ruff check .
mypy .
```

## CI/CD

- Pushes and pull requests run Ruff, Mypy, Pytest, a build check, `twine check`, and a CLI smoke test in GitHub Actions.
- Pushing a version tag that starts with `v` creates a GitHub Release and publishes the package to PyPI through Trusted Publishing.
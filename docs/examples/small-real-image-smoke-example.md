---
title: Small Real-Image OpenCV Calibration Smoke Example
description: Reproduce a three-image OpenCV checkerboard audit and understand why a passing smoke test is not a production calibration benchmark.
---

# Small Real-Image Smoke Example

This example proves that redistributable real-camera images can travel through
detection, calibration, JSON/CSV/YAML export, and the offline HTML report. It
is intentionally small and is **not a production-ready calibration dataset**.

## Data source and license

The repository includes three images derived without pixel changes from:

```text
OpenCV samples/data/left01.jpg
OpenCV samples/data/left02.jpg
OpenCV samples/data/left03.jpg
```

- Source repository: [opencv/opencv](https://github.com/opencv/opencv)
- Pinned source commit:
  [`e35ad60e4e1db55be854df5770f706af65803690`](https://github.com/opencv/opencv/commit/e35ad60e4e1db55be854df5770f706af65803690)
- License: Apache-2.0
- Resolution: 640 × 480, 8-bit grayscale JPEG
- Target: 9 × 6 inner corners
- Square size: not published; the example uses a nominal 30 mm scale

See the checked-in
[manifest and license](https://github.com/flavvesResearch/opencv-calibration-audit/tree/main/tests/fixtures/opencv-real).

## Reproduce the report

From a clone of the repository, install the project and decode the text-carried
fixtures:

```bash
python -m pip install -e .
python - <<'PY'
from base64 import b64decode
from pathlib import Path

source = Path("tests/fixtures/opencv-real")
destination = Path("real_checkerboards")
destination.mkdir(exist_ok=True)
for encoded in sorted(source.glob("*.jpg.base64")):
    output = destination / encoded.name.removesuffix(".base64")
    output.write_bytes(b64decode(encoded.read_text(encoding="ascii")))
PY
```

Run the audit:

```bash
calibration-audit analyze ./real_checkerboards \
  --cols 9 --rows 6 --square-size 30 --unit mm \
  --min-valid-images 3 \
  --min-board-area 0.01 \
  --output ./audit_result
```

The published artifact records this terminal summary:

```text
Quality gates: PASSED
Accepted views: 3
OpenCV RMS: 0.203403 px
Report: audit_result/report.html
```

[Open the report](../example-report/report.html) ·
[Open `summary.json`](../example-report/summary.json)

## Actual measurements

| Measurement | Value | Interpretation |
| --- | ---: | --- |
| Discovered images | 3 | All three files were readable |
| Accepted views | 3 | Two were accepted with warnings |
| Detection rate | 1.0 | Complete patterns in every image |
| Coverage ratio | 0.083333 | One occupied cell in a 4 × 3 grid |
| Occupied scale bins | 3 | Variation exists within this small set |
| Rotation range | 89.357° | Circular in-plane range |
| Duplicate views | 0 | No original source view rejected as duplicate |
| OpenCV RMS | 0.203403 px | In-sample aggregate residual |
| Mean per-view RMSE | 0.202607 px | Mean of the three per-view values |
| Image warnings | 2 | Near-border physical board boundary |
| Dataset warnings | 1 | Low field coverage |

The generated quality-gate list contains only `minimum_valid_images`, so the
result says `PASSED` despite three warnings. Passing means the configured gate
passed, not that this dataset is production quality.

## Make the warnings fail intentionally

Run the same analysis with a fresh output directory:

```bash
calibration-audit analyze ./real_checkerboards \
  --cols 9 --rows 6 --square-size 30 --unit mm \
  --min-valid-images 3 \
  --min-board-area 0.01 \
  --fail-on-warning \
  --output ./audit_result_strict
```

The completed audit writes its report, prints `Quality gates: FAILED`, and
returns exit code `1`. The strict gate counts the low-coverage warning and both
near-border image warnings.

## What this example proves

- The exact licensed samples are traceable and reproducible.
- OpenCV detects all three checkerboards.
- The full report/export path works with real camera data.
- Warnings remain visible even when the minimum-view gate passes.

It does not prove adequate field coverage, pose diversity, independent
accuracy, or production readiness. See the
[production benchmark requirements](production-dataset-benchmark.md).

_Documentation version: 0.2.2 · Updated: 2026-07-31_

---
title: Getting Started with OpenCV Calibration Dataset Validation
description: Install OpenCV Calibration Audit, analyze checkerboard images, and inspect the first HTML and JSON calibration-quality report.
---

# Audit Your First Checkerboard Dataset

This tutorial takes a folder of checkerboard images from installation to an
offline calibration-quality report. By the end, you will know which views were
accepted and where to find the evidence behind each decision.

## What you need

- Python 3.10–3.13.
- JPEG, PNG, BMP, TIFF, or WebP images from one camera at one resolution.
- A standard black-and-white checkerboard visible in the images.
- The checkerboard's inner-corner count and physical square size.

The tool uses the physical square size for calibration object points. Measure
the printed target; do not infer it from the image.

## Step 1: Install the package

Create or activate a virtual environment, then install from PyPI:

```bash
python -m pip install opencv-calibration-audit
calibration-audit --version
```

The second command prints the installed tool version.

## Step 2: Run the audit

For a target with 10 × 7 squares, pass 9 × 6 inner corners:

```bash
calibration-audit analyze ./calibration_images \
  --cols 9 \
  --rows 6 \
  --square-size 30 \
  --unit mm \
  --min-valid-images 10 \
  --output ./audit_result
```

A successful run prints a concise summary:

```text
Quality gates: PASSED
Accepted views: 12
OpenCV RMS: 0.284931 px
Report: audit_result/report.html
```

The exact counts and errors depend on your images. If fewer than 10 usable
views remain, the command exits with an input error instead of calibrating an
undersized set.

## Step 3: Review the report

Open `audit_result/report.html` in a browser. It is self-contained and needs no
CDN or internet connection.

Review these sections in order:

1. **Pass/fail quality gates** for the process result.
2. **Dataset counts and metrics** for detection, coverage, and diversity.
3. **Accepted, warning, and rejected images** for annotated per-image evidence.
4. **Reprojection-error chart** for views with large in-sample residuals.
5. **Metric limitations** before turning a value into a release threshold.

Use `audit_result/summary.json` in automation and `images.csv` to sort or
filter individual images.

## Add explicit quality gates

Defaults are deliberately conservative. Add thresholds based on your capture
setup and accuracy requirements:

```bash
calibration-audit analyze ./calibration_images \
  --cols 9 --rows 6 --square-size 30 --unit mm \
  --min-valid-images 15 \
  --min-board-area 0.05 \
  --max-per-view-error 1.0 \
  --fail-on-warning \
  --output ./audit_result
```

`--fail-on-warning` makes dataset-level and per-image warnings fail a quality
gate. It does not turn warnings into pre-calibration rejections.

## Troubleshooting

### The pattern is never found

Confirm that `--cols` and `--rows` count inner corners, the entire checkerboard
is visible, and the images are not severely blurred or overexposed. The
fallback classic detector is enabled unless
`--disable-fallback-detector` is set.

### The output directory already exists

Choose a new output path or deliberately replace only generator-managed files:

```bash
calibration-audit analyze ./calibration_images \
  --cols 9 --rows 6 --square-size 30 \
  --output ./audit_result \
  --overwrite-output
```

Unrelated files in that directory are preserved. The report manifest controls
which old generated files are removed.

### Recursive input rejects the output path

With `--recursive`, keep `--output` outside the input tree. This prevents a
previous report's thumbnails from becoming calibration input.

## Next steps

- Learn [how to validate dataset quality before `calibrateCamera`](guide/validate-opencv-camera-calibration-dataset.md).
- Review every [CLI option](reference/cli.md).
- Use the typed [Python API](reference/python-api.md).
- Understand the [coverage and diversity heuristics](concepts/coverage-and-diversity.md).

_Documentation version: 0.2.2 · Updated: 2026-07-31_

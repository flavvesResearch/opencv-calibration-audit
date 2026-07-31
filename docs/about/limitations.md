---
title: OpenCV Calibration Audit Scope and Limitations
description: Supported checkerboards, pinhole calibration scope, heuristic limits, input constraints, and unsupported camera-calibration workflows.
---

# Scope and Limitations

OpenCV Calibration Audit is a dataset diagnostic for standard checkerboard,
monocular, pinhole calibration. It explains image-level and dataset-level
signals; it does not certify a camera or guarantee downstream accuracy.

## Supported

- Standard black-and-white checkerboards.
- One camera and one readable image resolution per run.
- OpenCV pinhole calibration through `cv2.calibrateCamera`.
- Python 3.10–3.13.
- JPEG, PNG, BMP, TIFF, and WebP input.
- Unsigned 8-bit and 16-bit grayscale, BGR, and BGRA images.
- Local CLI and typed Python API use.
- Offline HTML plus JSON, CSV, YAML, and text outputs.

## Not supported

- Fisheye camera models.
- Stereo or multi-camera calibration.
- ChArUco, ArUco, asymmetric/symmetric circle grids, or custom fiducials.
- Partial-board calibration.
- Live capture guidance or automatic camera control.
- Automatic outlier pruning and recalibration.
- A desktop or web GUI.
- PDF report generation.
- ROS `camera_info` compatibility.
- Input image deletion, movement, rewriting, or repair.

## Measurement limits

### Sharpness

Variance of the Laplacian changes with resolution, target size, texture,
focus, optics, and image processing. Relative outlier detection is useful
within one dataset but is not a cross-camera sharpness standard.

### Exposure

Mean intensity and near-black/near-white ratios catch obvious failures. They do
not model local contrast, sensor linearity, high-dynamic-range acquisition, or
corner-level saturation.

### Coverage and diversity

Board-center grid occupancy, area bins, circular rotation range, and signed
perspective are explainable heuristics. They do not calculate parameter
observability, covariance, or full 3D pose distribution.

### Physical board boundary

The boundary is estimated by fitting a homography to inner corners and
projecting one square outward. It assumes a planar, regular checkerboard and
can become unreliable under extreme detection or target defects.

### Duplicates

Near-duplicate policy compares normalized 2D geometry, not image content or
calibrated 3D extrinsics. Threshold changes can retain redundancy or reject
useful nearby poses.

### Reprojection error

Per-view residuals are calculated on the same images used to fit the camera.
They are in-sample evidence, not held-out accuracy. A low RMS can coexist with
weak coverage or a mismatched camera model.

## Operational limits

- Files larger than 100 MiB are rejected by default in the Python
  configuration.
- Mixed readable resolutions stop the complete run.
- Non-empty output directories require explicit overwrite authorization.
- Recursive scans reject output paths inside the input tree.
- High reprojection error is reported after calibration; the model is not
  automatically refit without that view.

## What to use instead

Choose OpenCV's dedicated fisheye, stereo, ChArUco, or circle-grid APIs when
those models and targets match the task. Use held-out images, known physical
measurements, uncertainty analysis, or downstream task error for independent
validation.

Read [how the audit fits into a calibration workflow](../guide/validate-opencv-camera-calibration-dataset.md).

_Documentation version: 0.2.2 · Updated: 2026-07-31_

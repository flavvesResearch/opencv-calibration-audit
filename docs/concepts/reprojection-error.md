---
title: OpenCV Reprojection Error Explained
description: Interpret OpenCV RMS and per-view reprojection RMSE without mistaking in-sample residuals for independent calibration accuracy.
---

# OpenCV Reprojection Error and Camera Calibration Quality

Reprojection error measures the pixel distance between detected image corners
and object points projected through the fitted camera model. It is useful for
finding views the model explains poorly, but a low value alone does not prove
that the calibration is accurate outside the captured poses.

## Per-view statistics

For each accepted view, OpenCV Calibration Audit projects the checkerboard
object points using that view's fitted rotation and translation, then compares
the projected and detected 2D points.

For point errors `dx` and `dy`:

```text
rmse_px = sqrt(mean(dx² + dy²))
```

The report also records:

- `mean_px`: mean Euclidean point distance;
- `median_px`: median Euclidean point distance;
- `max_px`: largest point distance;
- `point_count`: number of compared corners.

All values are in pixels.

## OpenCV RMS versus mean per-view RMSE

`opencv_rms` is the value returned by `cv2.calibrateCamera`. The audit also
reports the arithmetic mean of the independently calculated per-view RMSE
values as `mean_per_view_rmse_px`.

They summarize related residuals but use different aggregation, so they need
not be numerically identical. Use per-view values to locate an outlier instead
of judging every view by the aggregate.

## Why this is in-sample evidence

The same accepted corners are used to:

1. fit camera intrinsics, distortion, and per-view extrinsics;
2. project the target points;
3. calculate residuals.

The model is therefore evaluated on its fitting data. Similar centered views
can produce a small residual while leaving edge distortion or other operating
poses weakly constrained.

For an independent accuracy claim, evaluate held-out images, measure known
geometry, or test the downstream vision task.

## Set a per-view gate

The CLI adds a quality gate only when a maximum is configured:

```bash
calibration-audit analyze ./calibration_images \
  --cols 9 --rows 6 --square-size 30 --unit mm \
  --max-per-view-error 1.0 \
  --output ./audit_result
```

A view above the threshold receives a `HIGH_REPROJECTION_ERROR` warning after
the initial calibration. The `maximum_per_view_reprojection_error` quality
gate fails and the CLI exits with code `1`.

Version 0.2.2 does not remove that view and recalibrate. Silent iterative
pruning can hide a systematic capture or model problem, so the report leaves
the decision visible to the operator.

## Choose a threshold

No universal pixel threshold applies to every camera. Consider:

- image resolution and corner localization precision;
- lens distortion and whether the pinhole model is suitable;
- target print quality and flatness;
- focus, motion blur, and depth of field;
- required metric or angular accuracy downstream.

Start with the residual distribution from a known capture process, inspect
annotated high-error views, and validate the chosen limit against independent
results.

## Related documentation

- [Validate an OpenCV calibration dataset](../guide/validate-opencv-camera-calibration-dataset.md)
- [Coverage and pose diversity](coverage-and-diversity.md)
- [Output schema](../reference/output-schema.md)
- [OpenCV calibration functions](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)

_Documentation version: 0.2.2 · Updated: 2026-07-31_

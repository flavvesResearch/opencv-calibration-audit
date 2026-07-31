---
title: Checkerboard Coverage and Pose Diversity for Camera Calibration
description: Understand image-plane coverage, target scale, circular rotation range, and perspective diversity in OpenCV checkerboard datasets.
---

# Coverage and Pose Diversity in Camera Calibration Images

Coverage and diversity describe where the checkerboard was observed and how
its pose changed. They complement reprojection error by exposing image sets
that fit but sample only a narrow part of the camera's field of view.

## Image-plane coverage

For each accepted view, the audit computes the center of the four outer
detected inner corners and normalizes it by image width and height. The default
4 × 3 grid increments the cell containing that center:

```text
coverage_ratio = occupied board-center cells / 12
```

The report also stores a `corner_density_grid`, which counts all detected
corner observations per grid cell. Board-center coverage is the decision
metric; corner density gives a more detailed view of where constraints exist.

### What the metric catches

A dataset of 20 centered boards can occupy one cell and produce
`coverage_ratio = 0.0833`. More files did not add new image-plane coverage.
Moving the target toward the edges and corners generally samples regions where
lens distortion is more visible.

### Trade-off

A center grid is interpretable and resolution-independent, but it loses
within-cell detail. A large tilted board can place corners across several
cells while its center occupies only one. Use the density grid and annotated
previews alongside the ratio.

## Physical board area and scale bins

Detected points are inner corners, not the physical target edge. The audit fits
a homography and projects a boundary one square beyond the outer inner-corner
rows and columns. Its area divided by image area is `board_area_ratio`.

Accepted area values are divided into five bins between the dataset minimum and
maximum. `occupied_scale_bins` counts non-empty bins.

This measures variation within the observed dataset. Three occupied bins do
not prove that the absolute near and far distances are suitable. If every view
has the same area, one bin is occupied.

## Circular rotation range

The target's top inner-corner row defines an in-plane angle. Angles wrap at
`-180°/180°`, so ordinary subtraction is wrong near the boundary.

The audit normalizes angles on a circle, finds the largest empty angular gap,
and reports:

```text
smallest covering arc = 360° - largest empty gap
```

Examples:

- `179°` and `-179°` span about `2°`;
- a single orientation spans `0°`;
- `0°`, `90°`, `180°`, and `-90°` require a `270°` covering arc.

The default low-pose-diversity warning threshold is `15°`.

## Signed perspective

For the quadrilateral formed by the outer detected inner corners:

```text
horizontal = (top_length - bottom_length) / max(top_length, bottom_length)
vertical   = (left_length - right_length) / max(left_length, right_length)
```

The signs retain tilt direction. A target tilted left and one tilted right
should not collapse into the same pose descriptor. Dataset metrics report the
maximum minus minimum for each signed component.

These ratios are projective shape summaries, not recovered 3D target angles.

## Capture guidance

Aim for:

- board centers across the center, edges, and corners;
- several target sizes created by changing distance;
- in-plane rotations rather than one horizontal orientation;
- target tilt in both horizontal and vertical directions;
- a fully visible physical checkerboard boundary.

Do not chase a metric by accepting blurred, clipped, or extremely oblique
views. All signals must remain usable together.

## Configuration

The Python API exposes the coverage grid and warning thresholds:

```python
config = AuditConfig(
    pattern=pattern,
    coverage_cols=4,
    coverage_rows=3,
    min_coverage_ratio=0.35,
    min_scale_bins=3,
    min_rotation_range_degrees=15.0,
)
```

These three diversity thresholds are Python API configuration in version
0.2.2; the CLI exposes their warnings through `--fail-on-warning` but does not
provide flags to change them.

See the [Python API reference](../reference/python-api.md) and the
[dataset-validation guide](../guide/validate-opencv-camera-calibration-dataset.md).

_Documentation version: 0.2.2 · Updated: 2026-07-31_

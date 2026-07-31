---
title: Detect Duplicate Camera Calibration Images by Pose
description: Learn how near-duplicate OpenCV checkerboard views are compared by center, scale, wrapped rotation, perspective, and sharpness.
---

# Detect Near-Duplicate Camera Calibration Views

Near-duplicate images add file count without adding much geometric evidence.
OpenCV Calibration Audit compares image-derived pose components before
calibration and keeps the sharper view when all components are sufficiently
close.

## Pose representation

Each complete checkerboard detection contributes:

- normalized board-center coordinates;
- physical board area divided by image area;
- in-plane rotation in degrees;
- signed horizontal perspective;
- signed vertical perspective.

The comparison uses normalized measurements so the default thresholds are not
tied to one pixel resolution.

## Component distances

Two views are duplicates only if every condition passes:

| Component | Distance | Default maximum |
| --- | --- | ---: |
| Center | Euclidean distance in normalized image coordinates | `0.03` |
| Scale | Absolute difference of log board areas | `0.08` |
| Rotation | Smallest wrapped angular difference | `5°` |
| Perspective | Euclidean distance across horizontal and vertical ratios | `0.08` |

The conjunction matters. Similar centers with clearly different target scale,
rotation, or tilt remain distinct.

## Which image is kept

Candidates are sorted by descending board-region sharpness and then by
case-insensitive relative path for deterministic ties. The first view becomes
the retained representative. A later match is rejected with:

```text
NEAR_DUPLICATE_POSE
Pose is near-duplicate of sharper view '<path>'.
```

Its `duplicate_of` field points to the retained image.

## Limits of the method

This is a heuristic comparison of 2D checkerboard geometry. It does not:

- compare raw image hashes or visual content;
- estimate extrinsics first and compare full 3D camera-to-board transforms;
- account for changes elsewhere in the scene;
- prove that two close views have identical calibration information.

Very tight defaults can retain redundant images; loose values can reject views
that contain useful differences. Inspect the annotated report when tuning.

## Configure duplicate policy in Python

```python
config = AuditConfig(
    pattern=pattern,
    duplicate_center_distance=0.03,
    duplicate_log_area_distance=0.08,
    duplicate_rotation_degrees=5.0,
    duplicate_perspective_distance=0.08,
)
```

These thresholds are available through the Python API in version 0.2.2. The
CLI uses their defaults.

## Related documentation

- [Coverage and pose diversity](coverage-and-diversity.md)
- [Decision codes](../reference/decision-codes.md)
- [Python API configuration](../reference/python-api.md)

_Documentation version: 0.2.2 · Updated: 2026-07-31_

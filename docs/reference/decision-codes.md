---
title: Calibration Dataset Decision and Reason Codes
description: Stable reason-code reference for unreadable, rejected, warning, duplicate, coverage, diversity, and reprojection decisions.
---

# Decision States and Reason Codes

Each image reason has a stable `code`, a `severity`, a human-readable message,
the measured value when available, and the threshold or rule. Dataset-level
warnings use the same `AuditReason` shape.

## Image states

| State | Rule | Calibrated |
| --- | --- | --- |
| `ACCEPTED` | Readable, detected, no reasons | Yes |
| `WARNING` | Readable and usable with warning reasons | Yes |
| `REJECTED` | At least one `ERROR` reason | No |
| `UNREADABLE` | Decode or representation failed | No |

## Read and detection codes

| Code | Usual severity | Meaning |
| --- | --- | --- |
| `IMAGE_UNREADABLE` | `ERROR` | File metadata or encoded image could not be read |
| `UNSUPPORTED_IMAGE` | `ERROR` | Decoded dtype or channel layout is unsupported |
| `RESOLUTION_MISMATCH` | `ERROR` | Public code for inconsistent resolution decisions; current pipeline stops the dataset with a grouped validation error |
| `PATTERN_NOT_FOUND` | `ERROR` | No complete checkerboard detection |
| `PARTIAL_PATTERN` | `ERROR` | Detector returned corners but not the requested complete pattern |

## Board geometry and image quality

| Code | Usual severity | Meaning |
| --- | --- | --- |
| `BOARD_TOO_SMALL` | `ERROR` | Physical board-area ratio is below `min_board_area` |
| `BOARD_TOO_LARGE` | `ERROR` | Physical board-area ratio is above `max_board_area` |
| `BOARD_CLIPPED_OR_NEAR_BORDER` | `WARNING` | Estimated physical checkerboard boundary is closer than `near_border_ratio` or outside the frame |
| `LOW_SHARPNESS` | `WARNING` or `ERROR` | Relative low outlier when no threshold is set; rejection when explicit `min_sharpness` fails |
| `EXPOSURE_TOO_DARK` | `WARNING` | Mean intensity `< 30` or near-black ratio `> 0.40` |
| `EXPOSURE_TOO_BRIGHT` | `WARNING` | Mean intensity `> 225` or near-white ratio `> 0.40` |

Near-black pixels are grayscale values `≤ 5`; near-white pixels are `≥ 250`
after supported input normalization.

## Pose and calibration codes

| Code | Usual severity | Meaning |
| --- | --- | --- |
| `NEAR_DUPLICATE_POSE` | `ERROR` | View matches a sharper retained view across all duplicate components |
| `HIGH_REPROJECTION_ERROR` | `WARNING` | Post-calibration per-view RMSE exceeds `max_per_view_error` |
| `INSUFFICIENT_VALID_IMAGES` | `ERROR` | Public reason code for too few views; current pipeline raises `InsufficientViewsError` before creating a result |

High reprojection error does not remove and recalibrate a view in version
0.2.2.

## Dataset warning codes

| Code | Severity | Meaning |
| --- | --- | --- |
| `LOW_FIELD_COVERAGE` | `WARNING` | Board-center coverage ratio is below `min_coverage_ratio` |
| `LOW_SCALE_DIVERSITY` | `WARNING` | Occupied board-area bins are below `min_scale_bins` |
| `LOW_POSE_DIVERSITY` | `WARNING` | Circular rotation range is below `min_rotation_range_degrees` |

Dataset warnings appear in top-level `warnings`, not within a particular
image. `--fail-on-warning` counts both dataset and image warning reasons.

## Quality gate names

| Gate | Created when | Pass condition |
| --- | --- | --- |
| `minimum_valid_images` | Always in a completed result | Accepted count met the configured minimum |
| `maximum_per_view_reprojection_error` | `max_per_view_error` is set | No calibrated view exceeds the limit |
| `fail_on_warning` | `fail_on_warning=True` | Zero dataset and image warnings |

Too few accepted views raises `InsufficientViewsError`, so no completed output
is written with a failed `minimum_valid_images` gate.

## Related

- [CLI exit codes](cli.md#exit-codes)
- [Output schema](output-schema.md)
- [Duplicate-view logic](../concepts/duplicate-views.md)

_Documentation version: 0.2.2 · Updated: 2026-07-31_

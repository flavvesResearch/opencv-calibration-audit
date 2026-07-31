---
title: Calibration Audit JSON, CSV, YAML, and HTML Output Schema
description: Reference for summary.json, images.csv, calibration.yaml, report.html, manifests, and accepted or rejected image lists.
---

# Output Files and JSON Schema

`AuditResult.write_outputs` and the CLI write a deterministic report directory
for people and automation.

## Directory layout

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
        └── <path-hash>.jpg
```

## `summary.json`

The top-level object uses `schema_version: 1`.

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | Serialized contract version |
| `tool_version` | string | Package version that produced the output |
| `opencv_version` | string or null | Runtime OpenCV version |
| `generated_at` | ISO 8601 string | Local timezone-aware generation time |
| `input_directory` | string | `"."`; absolute source paths are not serialized |
| `configuration` | object | Effective configuration except runtime input/output paths |
| `pattern` | object | `cols`, `rows`, `square_size`, and `unit` |
| `dataset_metrics` | object | Dataset counts, coverage, diversity, and duplicates |
| `quality_gates` | array | Gate name, result, message, value, and threshold |
| `calibration` | object | Pinhole calibration result |
| `images` | array | Per-image detection, metrics, decision, and residual |
| `warnings` | array | Dataset-level `AuditReason` objects |
| `errors` | array | Dataset-level `AuditReason` objects |
| `passed` | boolean | Derived result: every quality gate passed |

### `dataset_metrics`

Counts:

```text
discovered_count readable_count detected_count accepted_count
warning_count rejected_count unreadable_count duplicate_count
```

Detection and coverage:

```text
detection_rate
coverage_grid
occupied_coverage_cells
coverage_ratio
corner_density_grid
```

Scale and pose:

```text
scale_min scale_max scale_median scale_iqr occupied_scale_bins
rotation_range_degrees
horizontal_perspective_range
vertical_perspective_range
```

Scale and pose values can be `null` when no usable measurement exists.

### `images[]`

| Field | Type | Meaning |
| --- | --- | --- |
| `relative_path` | string | POSIX-style path relative to input |
| `read_success` | boolean | Image decoded to a supported representation |
| `detection_success` | boolean | Complete checkerboard detected |
| `detection_method` | string or null | OpenCV detector used |
| `detection_duration_ms` | number or null | Detection wall time |
| `corner_count` | integer | Returned inner-corner count |
| `corners` | array | `[x, y]` image coordinates |
| `metrics` | object | Image, sharpness, exposure, and target geometry |
| `state` | string | `ACCEPTED`, `WARNING`, `REJECTED`, or `UNREADABLE` |
| `reasons` | array | Stable code, severity, explanation, measurement, rule |
| `duplicate_of` | string or null | Retained sharper view for a duplicate |
| `reprojection` | object or null | Per-view residual statistics after calibration |

`metrics` includes width, height, channels, original dtype/bit depth, file size,
global and board sharpness, sharpness decision source, exposure measures,
normalized board center, projected physical boundary, area, rotation,
perspective ratios, and normalized border distance.

### `calibration`

| Field | Type | Meaning |
| --- | --- | --- |
| `camera_model` | string | `"pinhole"` |
| `image_size` | two integers | Width and height |
| `opencv_rms` | number | RMS returned by `cv2.calibrateCamera` |
| `camera_matrix` | 3 × 3 numbers | Intrinsic camera matrix |
| `distortion_coefficients` | array | OpenCV distortion vector |
| `rotation_vectors` | array | Per-view Rodrigues vectors |
| `translation_vectors` | array | Per-view translations in metres |
| `calibration_flags` | integer | Flags passed to OpenCV; currently `0` by default |
| `mean_per_view_rmse_px` | number | Arithmetic mean of per-view RMSE |

## `images.csv`

One row per discovered image with these columns:

```text
relative_path, read_success, resolution, detection_success, detection_method,
original_dtype, original_bit_depth, global_sharpness, board_sharpness,
board_center_x, board_center_y, board_area_ratio, rotation_degrees,
horizontal_perspective, vertical_perspective, duplicate_of, final_state,
reason_codes, reprojection_rmse_px
```

Multiple reason codes are separated with `|`.

## `calibration.yaml`

The YAML file carries image dimensions, the `pinhole` model, a flattened
OpenCV-style 3 × 3 camera matrix, distortion coefficients, aggregate
reprojection values, and pattern information. It does not claim ROS
`camera_info` compatibility.

## Text lists

`accepted.txt` includes both `ACCEPTED` and `WARNING` views because both were
used for calibration. `rejected.txt` includes `REJECTED` and `UNREADABLE`
paths. Each path occupies one line.

## `report.html`

The report embeds CSS, charts, and annotated JPEG previews as data URLs. It has
no external network dependency. Untrusted filenames and messages are HTML
escaped.

## `report-manifest.json`

The manifest contains:

```json
{
  "manifest_version": 1,
  "generated_files": [
    "accepted.txt",
    "assets/coverage_heatmap.png"
  ]
}
```

The actual list includes every generator-owned file in sorted order. On an
authorized overwrite, only listed paths and legacy numbered thumbnails are
removed; unrelated files are preserved.

## Compatibility guidance

Check `schema_version` before parsing. Additive fields may appear in future
tool releases. Do not scrape `report.html` or terminal prose for automation.

[Inspect the published smoke `summary.json`](../example-report/summary.json) or
use the [Python API](python-api.md).

_Documentation version: 0.2.2 · Updated: 2026-07-31_

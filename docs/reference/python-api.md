---
title: OpenCV Calibration Audit Python API Reference
description: Typed Python API reference for audit_dataset, AuditConfig, checkerboard patterns, result models, thresholds, and exceptions.
---

# Python API Reference

The public `calibration_audit` package exposes typed Pydantic configuration and
result models. Library functions raise domain exceptions and never call
`sys.exit()`.

## Basic use

```python
from pathlib import Path

from calibration_audit import AuditConfig, PatternSpec, audit_dataset

pattern = PatternSpec(cols=9, rows=6, square_size=30.0, unit="mm")
config = AuditConfig(
    pattern=pattern,
    min_valid_images=12,
    max_per_view_error=1.0,
)

result = audit_dataset(Path("./calibration_images"), config)
print(result.summary)
result.write_outputs(Path("./audit_result"))
```

## `audit_dataset`

```python
audit_dataset(image_directory: Path, config: AuditConfig) -> AuditResult
```

Discovers and analyzes images, rejects unusable views, calibrates all accepted
pre-calibration views, calculates dataset metrics and quality gates, and
returns an `AuditResult`. It does not write output files.

## `PatternSpec`

| Field | Type | Constraint / default |
| --- | --- | --- |
| `cols` | `int` | Required, ≥ 2 inner corners |
| `rows` | `int` | Required, ≥ 2 inner corners |
| `square_size` | `float` | Required, > 0 |
| `unit` | `"mm" \| "cm" \| "inch" \| "m"` | `"mm"` |

Properties:

- `pattern_size -> tuple[int, int]` returns `(cols, rows)`;
- `square_size_metres -> float` converts the supplied size to metres.

Unknown fields, `NaN`, and infinite values are rejected.

## `AuditConfig`

### Input, output, and execution

| Field | Type | Default | Constraint / behavior |
| --- | --- | --- | --- |
| `pattern` | `PatternSpec` | required | Checkerboard geometry |
| `image_directory` | `Path \| None` | `None` | Deprecated convenience value; pass the path to `audit_dataset` |
| `output` | `Path` | `./calibration-audit-output` | Used to validate recursive output placement |
| `recursive` | `bool` | `False` | Scan subdirectories |
| `disable_fallback_detector` | `bool` | `False` | Disable classic detector fallback |
| `fail_on_warning` | `bool` | `False` | Add a zero-warning quality gate |
| `overwrite_output` | `bool` | `False` | CLI convenience; pass `overwrite` to `write_outputs` in library code |
| `log_level` | `DEBUG \| INFO \| WARNING \| ERROR` | `INFO` | CLI logging level |
| `max_file_size_mb` | `int` | `100` | 1–4096 MiB per input file |

### Image policy

| Field | Type | Default | Constraint / behavior |
| --- | --- | ---: | --- |
| `min_valid_images` | `int` | `10` | > 0 |
| `min_board_area` | `float` | `0.03` | 0–1 exclusive |
| `max_board_area` | `float` | `0.90` | 0–1 exclusive and greater than minimum |
| `min_sharpness` | `float \| None` | `None` | > 0 when set; turns low sharpness into rejection |
| `max_per_view_error` | `float \| None` | `None` | > 0 pixels when set |
| `near_border_ratio` | `float` | `0.01` | 0 inclusive to 0.5 exclusive |
| `relative_sharpness_factor` | `float` | `0.35` | 0–1 exclusive |

### Duplicate policy

| Field | Type | Default | Constraint |
| --- | --- | ---: | --- |
| `duplicate_center_distance` | `float` | `0.03` | > 0 |
| `duplicate_log_area_distance` | `float` | `0.08` | > 0 |
| `duplicate_rotation_degrees` | `float` | `5.0` | > 0 and ≤ 180 |
| `duplicate_perspective_distance` | `float` | `0.08` | > 0 |

### Coverage and diversity

| Field | Type | Default | Constraint |
| --- | --- | ---: | --- |
| `coverage_cols` | `int` | `4` | 1–32 |
| `coverage_rows` | `int` | `3` | 1–32 |
| `min_coverage_ratio` | `float` | `0.35` | 0–1 inclusive |
| `min_scale_bins` | `int` | `3` | 1–5 |
| `min_rotation_range_degrees` | `float` | `15.0` | 0–360 |

`config.policy` returns an `AuditPolicy` copy containing the decision
thresholds.

## `AuditPolicy`

`AuditPolicy` is the measurement-independent threshold model used by metric
comparisons. It contains:

```text
min_valid_images
min_board_area
max_board_area
min_sharpness
max_per_view_error
near_border_ratio
relative_sharpness_factor
duplicate_center_distance
duplicate_log_area_distance
duplicate_rotation_degrees
duplicate_perspective_distance
min_coverage_ratio
min_scale_bins
min_rotation_range_degrees
```

Defaults and constraints match the corresponding `AuditConfig` fields.

## `AuditResult`

Important attributes:

| Attribute | Type | Meaning |
| --- | --- | --- |
| `schema_version` | `int` | Output contract version; currently `1` |
| `tool_version` | `str` | Package version |
| `opencv_version` | `str \| None` | Runtime OpenCV version |
| `pattern` | `PatternSpec` | Checkerboard specification |
| `dataset_metrics` | `DatasetMetrics` | Counts, coverage, diversity, duplicates |
| `quality_gates` | `list[QualityGateResult]` | Configured pass/fail checks |
| `calibration` | `CalibrationResult` | Pinhole calibration parameters |
| `images` | `list[ImageAuditResult]` | Per-image facts and decisions |
| `warnings` | `list[AuditReason]` | Dataset-level warnings |
| `errors` | `list[AuditReason]` | Dataset-level errors |

Properties and methods:

```python
result.passed                         # all quality gates passed
result.summary                        # concise dict for display
result.source_directory               # runtime source root
result.write_outputs(path)            # refuse non-empty output
result.write_outputs(path, overwrite=True)
```

`write_outputs` never modifies source images.

## Result models

- `ImageAuditResult`: relative path, read/detection facts, corners,
  `ImageMetrics`, state, reasons, duplicate source, and optional reprojection.
- `ImageMetrics`: image metadata, sharpness, exposure, normalized target
  geometry, perspective, and border distance.
- `DatasetMetrics`: file counts, detection rate, coverage grids, scale
  distribution, rotation/perspective ranges, and duplicate count.
- `CalibrationResult`: pinhole model, image size, OpenCV RMS, camera matrix,
  distortion, per-view extrinsics, flags, and mean per-view RMSE.
- `ReprojectionStats`: RMSE, mean, median, maximum pixel error, and point count.
- `QualityGateResult`: gate name, boolean result, message, measured value, and
  threshold.
- `AuditReason`: `ReasonCode`, `Severity`, message, measured value, and
  threshold/rule.

All public models forbid unknown fields. See [output schema](output-schema.md)
for serialized field-by-field structure.

## Enums

```python
ImageState.ACCEPTED
ImageState.WARNING
ImageState.REJECTED
ImageState.UNREADABLE

Severity.WARNING
Severity.ERROR
```

`ReasonCode` contains the stable codes listed in the
[decision-code reference](decision-codes.md).

## Exceptions

All library exceptions inherit `CalibrationAuditError`:

| Exception | Meaning |
| --- | --- |
| `InvalidConfigurationError` | Invalid domain configuration |
| `DatasetValidationError` | Invalid input path, dataset, resolution, or output placement |
| `UnsupportedImageError` | Unsupported decoded dtype or channel layout |
| `InsufficientViewsError` | Too few valid views remain |
| `CalibrationFailedError` | OpenCV calibration fails or returns non-finite values |
| `OutputExistsError` | Output path is invalid or a non-empty directory was not authorized |

Pydantic field validation raises `pydantic.ValidationError`.

## Package version

```python
from calibration_audit import __version__
```

For installed distributions, the version is read from package metadata.

_Documentation version: 0.2.2 · Updated: 2026-07-31_

---
title: OpenCV Calibration Audit CLI Reference
description: Complete calibration-audit command reference with checkerboard arguments, dataset thresholds, output behavior, and exit codes.
---

# Command-Line Interface Reference

The `calibration-audit` command analyzes checkerboard images, calibrates an
OpenCV pinhole camera from usable views, writes reports, and returns a
machine-readable exit status.

## Synopsis

```bash
calibration-audit analyze IMAGE_DIRECTORY \
  --cols COLS \
  --rows ROWS \
  --square-size SIZE \
  [OPTIONS]
```

```bash
calibration-audit --version
calibration-audit --help
calibration-audit analyze --help
```

## Required arguments

| Argument | Type | Meaning |
| --- | --- | --- |
| `IMAGE_DIRECTORY` | path | Directory containing calibration images |
| `--cols` | integer ≥ 2 | Inner corners horizontally |
| `--rows` | integer ≥ 2 | Inner corners vertically |
| `--square-size` | float > 0 | Physical checkerboard square side length |

`--cols` and `--rows` count inner corners, not squares.

## Options

| Option | Default | Effect |
| --- | --- | --- |
| `--unit {mm,cm,inch,m}` | `mm` | Unit of `--square-size` |
| `--output PATH` | `./calibration-audit-output` | Report directory |
| `--recursive` | off | Scan supported files in subdirectories |
| `--min-valid-images INT` | `10` | Minimum accepted views required before calibration |
| `--min-board-area FLOAT` | `0.03` | Reject a physical board-area ratio below this value |
| `--max-board-area FLOAT` | `0.90` | Reject a physical board-area ratio above this value |
| `--min-sharpness FLOAT` | unset | Reject board-region Laplacian variance below this value |
| `--max-per-view-error FLOAT` | unset | Fail a quality gate when a per-view RMSE exceeds this pixel value |
| `--disable-fallback-detector` | off | Do not try classic `findChessboardCorners` after the SB detector |
| `--fail-on-warning` | off | Add a gate that fails when any dataset or image warning exists |
| `--overwrite-output` | off | Replace generator-managed output files in a non-empty directory |
| `--log-level {DEBUG,INFO,WARNING,ERROR}` | `INFO` | Logging verbosity; `DEBUG` includes tracebacks |

`--min-board-area` must be smaller than `--max-board-area`. Ratios must be
strictly between zero and one.

## Supported input

Extensions are matched case-insensitively:

```text
.jpg .jpeg .png .bmp .tif .tiff .webp
```

Unsigned 8-bit and unsigned 16-bit grayscale, BGR, and BGRA data are supported.
All readable files must have one resolution. Recursive discovery ignores
symlinks that resolve outside the requested input tree.

## Output behavior

The command refuses a non-empty output directory unless
`--overwrite-output` is present. Overwrite removes files declared by the prior
`report-manifest.json` plus legacy numbered thumbnails; unrelated files remain.

With `--recursive`, the resolved output directory must be outside the input
tree.

See [output schema](output-schema.md) for every generated file.

## Terminal output

A completed audit prints:

```text
Quality gates: PASSED
Accepted views: 12
OpenCV RMS: 0.284931 px
Report: audit_result/report.html
```

Informational processing logs go through Python logging. Use
`--log-level WARNING` when a quiet CI log is preferred.

## Exit codes

| Code | Meaning |
| ---: | --- |
| `0` | Audit completed and all configured quality gates passed |
| `1` | Audit completed, outputs were written, and a quality gate failed |
| `2` | Invalid arguments, configuration, input dataset, or output location |
| `3` | Processing or calibration failure, including unexpected failures |

Tracebacks are hidden unless `--log-level DEBUG` is active.

## Example

```bash
calibration-audit analyze ./images \
  --cols 9 --rows 6 \
  --square-size 25 --unit mm \
  --recursive \
  --min-valid-images 15 \
  --min-board-area 0.05 \
  --max-per-view-error 1.0 \
  --fail-on-warning \
  --output ../reports/camera-a \
  --overwrite-output
```

## Related

- [Getting started](../getting-started.md)
- [Python API](python-api.md)
- [Decision codes](decision-codes.md)

_Documentation version: 0.2.2 · Updated: 2026-07-31_

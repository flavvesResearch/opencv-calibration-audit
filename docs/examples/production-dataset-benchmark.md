---
title: Production Camera Calibration Dataset Benchmark Protocol
description: Reproducible benchmark protocol for a licensed real-camera checkerboard dataset with coverage, diversity, duplicate, and reprojection evidence.
---

# Production Dataset Benchmark

No production-quality real-camera benchmark is published yet. The repository's
three-image smoke example is too small and has weak image-plane coverage.
This page defines the evidence required before a benchmark can be presented as
complete; it does not invent images or results.

!!! warning "Current status: data required"
    A redistributable, clearly licensed real-camera checkerboard dataset with at
    least 15 accepted views has not been added to this repository. Benchmark
    numbers remain intentionally absent until that data and its provenance are
    available.

## Dataset acceptance requirements

The capture should contain:

- at least 15 accepted real-camera images at one resolution;
- board centers in multiple image-plane regions;
- at least three occupied scale bins;
- varied in-plane board rotations;
- signed perspective changes in both horizontal and vertical directions;
- a small controlled set of poor images, such as blur, exposure failure,
  near-duplicate pose, and clipped physical board boundary.

Synthetic images may be useful for regression tests but must not be described
as real-camera benchmark data.

## Provenance requirements

Add a `MANIFEST.md` beside the dataset containing:

```text
Source name and URL
Pinned source version or commit
Copyright holder
Redistribution license and local license file
Camera information, when published
Resolution and image encoding
Checkerboard inner-corner count
Physical square size and unit
Every transformation or derived bad-image operation
File checksums
```

Do not download or redistribute a dataset whose license is unclear.

## Reproduction command

Once the dataset is approved, the benchmark page must publish the exact
versioned command. A starting policy is:

```bash
calibration-audit analyze ./benchmark_images \
  --cols 9 --rows 6 \
  --square-size 30 --unit mm \
  --min-valid-images 15 \
  --min-board-area 0.03 \
  --max-per-view-error 1.0 \
  --fail-on-warning \
  --output ./benchmark_result
```

The actual pattern, physical square size, and thresholds must match the
selected dataset and documented validation objective.

## Required result table

Populate this table directly from the generated `summary.json`; do not enter
plausible-looking values by hand.

| Measurement | Value | Threshold / interpretation |
| --- | ---: | --- |
| Discovered images | Not available | Informational |
| Accepted views | Not available | Target ≥ 15 |
| Detection rate | Not available | Explain unreadable and not-found views |
| Coverage ratio | Not available | Compare with configured threshold |
| Occupied scale bins | Not available | Target ≥ 3 |
| Rotation range | Not available | Degrees on a circular range |
| Duplicate views | Not available | Name rejected/retained pairs |
| OpenCV RMS | Not available | Pixels; in-sample |
| Mean per-view RMSE | Not available | Pixels; in-sample |
| Warnings and rejections | Not available | List stable reason codes |

## Verification checklist

Before changing this page's status:

1. Confirm the license permits repository redistribution.
2. Verify file hashes and documented transformations.
3. Run the benchmark from a clean environment.
4. Store the command, tool version, OpenCV version, and generated report.
5. Cross-check table values against `summary.json`.
6. Review annotated decisions rather than relying on aggregate metrics.
7. Keep an independent validation claim separate from in-sample residuals.

The [small real-image smoke example](small-real-image-smoke-example.md) remains
the reproducible end-to-end proof until this blocker is resolved.

_Documentation version: 0.2.2 · Updated: 2026-07-31_

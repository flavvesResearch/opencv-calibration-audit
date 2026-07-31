# Changelog

All notable changes to this project will be documented here.

## Unreleased

### Fixed

- Calculate board-rotation diversity on a circle across the `-180°/180°`
  boundary.
- Preserve horizontal and vertical perspective direction so opposite tilts are
  not treated as duplicate poses.
- Estimate the physical checkerboard boundary one square beyond the detected
  inner-corner grid for target area and border safety.
- Normalize unsigned 16-bit TIFF inputs with a fixed full-range mapping and
  record their original dtype and bit depth.
- Reject recursive audits whose output resolves inside the input tree.
- Remove stale generator-owned report assets using an output manifest while
  preserving unrelated files.

### Changed

- Embed mapped, annotated image previews and full decision evidence in the HTML
  report.
- Record the OpenCV runtime version in `summary.json`.
- Raise the tested OpenCV 4.x minimum to 4.11 and add explicit OpenCV 4.11/5.x
  CI jobs.
- Require Python 3.10 or newer and remove the Python 3.9 CI job.
- Restore automatic version tag and GitHub Release creation after successful
  `main` CI and explicitly dispatch PyPI Trusted Publishing after creation.

### Testing

- Add regressions for F-01 through F-07 and a small Apache-2.0 real-camera
  checkerboard fixture derived from OpenCV's calibration samples.

## 0.2.0 - 2026-07-30

- Implement the complete checkerboard dataset audit pipeline.
- Add explainable image policy, duplicate-pose filtering, pinhole calibration,
  per-view reprojection statistics, and offline reports.
- Add synthetic integration tests and extensive validation/error tests.
- Restrict package publishing to explicitly published GitHub Releases.

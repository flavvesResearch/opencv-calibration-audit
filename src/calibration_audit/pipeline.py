"""End-to-end checkerboard dataset audit pipeline."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from statistics import median

import numpy as np
import numpy.typing as npt

from .calibration import calibrate
from .config import AuditConfig
from .detection import detect_checkerboard
from .exceptions import DatasetValidationError, InsufficientViewsError
from .io import discover_images, load_image
from .metrics import (
    board_geometry,
    coverage_metrics,
    exposure_metrics,
    is_duplicate_pose,
    sharpness_metrics,
)
from .models import (
    AuditReason,
    AuditResult,
    DatasetMetrics,
    ImageAuditResult,
    ImageMetrics,
    ImageState,
    QualityGateResult,
    ReasonCode,
    Severity,
)

log = logging.getLogger(__name__)


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _reason(
    code: ReasonCode,
    severity: Severity,
    message: str,
    measured: float | str | None = None,
    threshold: float | str | None = None,
) -> AuditReason:
    return AuditReason(
        code=code,
        severity=severity,
        message=message,
        measured_value=measured,
        threshold=threshold,
    )


def _has_error(image: ImageAuditResult) -> bool:
    return any(reason.severity == Severity.ERROR for reason in image.reasons)


def _usable(images: Iterable[ImageAuditResult]) -> list[ImageAuditResult]:
    return [
        image
        for image in images
        if image.read_success and image.detection_success and not _has_error(image)
    ]


def _apply_relative_sharpness(images: list[ImageAuditResult], factor: float) -> None:
    candidates = _usable(images)
    values = [
        image.metrics.board_sharpness
        for image in candidates
        if image.metrics.board_sharpness is not None
    ]
    if not values:
        return
    reference = float(median(values))
    threshold = reference * factor
    for image in candidates:
        value = image.metrics.board_sharpness
        if value is not None and value < threshold:
            image.metrics.sharpness_decision_source = "relative_outlier"
            image.reasons.append(
                _reason(
                    ReasonCode.LOW_SHARPNESS,
                    Severity.WARNING,
                    "Board-region sharpness is a low outlier relative to this dataset.",
                    value,
                    f"{factor:g} × dataset median ({reference:.6g})",
                )
            )


def _apply_duplicates(images: list[ImageAuditResult], config: AuditConfig) -> None:
    candidates = _usable(images)
    candidates.sort(
        key=lambda image: (
            -(image.metrics.board_sharpness or 0.0),
            image.relative_path.casefold(),
        )
    )
    kept: list[ImageAuditResult] = []
    for candidate in candidates:
        duplicate = next(
            (
                accepted
                for accepted in kept
                if is_duplicate_pose(candidate.metrics, accepted.metrics, config.policy)
            ),
            None,
        )
        if duplicate is None:
            kept.append(candidate)
            continue
        candidate.duplicate_of = duplicate.relative_path
        candidate.reasons.append(
            _reason(
                ReasonCode.NEAR_DUPLICATE_POSE,
                Severity.ERROR,
                f"Pose is near-duplicate of sharper view '{duplicate.relative_path}'.",
                candidate.metrics.board_sharpness,
                "component-wise configured pose thresholds",
            )
        )


def _finalize_states(images: list[ImageAuditResult]) -> None:
    for image in images:
        if not image.read_success:
            image.state = ImageState.UNREADABLE
        elif _has_error(image):
            image.state = ImageState.REJECTED
        elif image.reasons:
            image.state = ImageState.WARNING
        else:
            image.state = ImageState.ACCEPTED


def _diversity(
    accepted: list[ImageAuditResult],
) -> tuple[float | None, float | None, float | None, float | None, int, float | None, float | None, float | None]:
    areas = sorted(
        image.metrics.board_area_ratio
        for image in accepted
        if image.metrics.board_area_ratio is not None
    )
    rotations = [
        image.metrics.rotation_degrees
        for image in accepted
        if image.metrics.rotation_degrees is not None
    ]
    horizontal = [
        image.metrics.horizontal_perspective
        for image in accepted
        if image.metrics.horizontal_perspective is not None
    ]
    vertical = [
        image.metrics.vertical_perspective
        for image in accepted
        if image.metrics.vertical_perspective is not None
    ]
    if not areas:
        return None, None, None, None, 0, None, None, None
    quartiles = np.percentile(np.asarray(areas), [25, 75])
    minimum, maximum = min(areas), max(areas)
    if math.isclose(minimum, maximum):
        occupied_bins = 1
    else:
        occupied_bins = int(
            np.count_nonzero(np.histogram(areas, bins=5, range=(minimum, maximum))[0])
        )
    return (
        minimum,
        maximum,
        float(np.median(areas)),
        float(quartiles[1] - quartiles[0]),
        occupied_bins,
        max(rotations) - min(rotations) if rotations else None,
        max(horizontal) - min(horizontal) if horizontal else None,
        max(vertical) - min(vertical) if vertical else None,
    )


def audit_dataset(image_directory: Path, config: AuditConfig) -> AuditResult:
    """Audit, calibrate, and return typed results without writing output files."""

    directory = Path(image_directory)
    paths = discover_images(directory, recursive=config.recursive)
    results: list[ImageAuditResult] = []
    corner_arrays: dict[str, npt.NDArray[np.float32]] = {}
    resolution_groups: dict[tuple[int, int], list[str]] = {}
    max_bytes = config.max_file_size_mb * 1024 * 1024

    for index, path in enumerate(paths, start=1):
        relative = path.relative_to(directory).as_posix()
        log.info("Processing image %d/%d: %s", index, len(paths), relative)
        try:
            _, gray, channels = load_image(path, max_file_size_bytes=max_bytes)
        except DatasetValidationError as exc:
            results.append(
                ImageAuditResult(
                    relative_path=relative,
                    metrics=ImageMetrics(file_size=_file_size(path)),
                    state=ImageState.UNREADABLE,
                    reasons=[
                        _reason(
                            ReasonCode.IMAGE_UNREADABLE,
                            Severity.ERROR,
                            str(exc),
                        )
                    ],
                )
            )
            log.warning("%s", exc)
            continue

        height, width = gray.shape
        resolution_groups.setdefault((width, height), []).append(relative)
        metrics = ImageMetrics(
            width=width,
            height=height,
            channels=channels,
            file_size=_file_size(path),
        )
        found, corners, method, duration = detect_checkerboard(
            gray, config.pattern, fallback=not config.disable_fallback_detector
        )
        image = ImageAuditResult(
            relative_path=relative,
            read_success=True,
            detection_success=found,
            detection_method=method,
            detection_duration_ms=duration,
            corner_count=0 if corners is None else int(corners.shape[0]),
            corners=[] if corners is None else corners.astype(float).tolist(),
            metrics=metrics,
        )
        log.debug(
            "Detection %s: success=%s method=%s corners=%d duration_ms=%.3f",
            relative,
            found,
            method,
            image.corner_count,
            duration,
        )
        if not found or corners is None:
            code = (
                ReasonCode.PARTIAL_PATTERN
                if corners is not None and corners.shape[0] > 0
                else ReasonCode.PATTERN_NOT_FOUND
            )
            image.reasons.append(
                _reason(code, Severity.ERROR, "Complete checkerboard pattern was not detected.")
            )
            results.append(image)
            continue

        geometry = board_geometry(corners, config.pattern, (width, height))
        metrics.board_center = geometry["board_center"]
        metrics.board_area_ratio = geometry["board_area_ratio"]
        metrics.rotation_degrees = geometry["rotation_degrees"]
        metrics.horizontal_perspective = geometry["horizontal_perspective"]
        metrics.vertical_perspective = geometry["vertical_perspective"]
        metrics.border_distance_ratio = geometry["border_distance_ratio"]
        metrics.global_sharpness, metrics.board_sharpness = sharpness_metrics(
            gray, corners, config.pattern
        )
        metrics.mean_intensity, metrics.near_black_ratio, metrics.near_white_ratio = (
            exposure_metrics(gray)
        )
        log.debug(
            "Metrics %s: area=%.6f center=%s sharpness=%.3f rotation=%.3f",
            relative,
            metrics.board_area_ratio,
            metrics.board_center,
            metrics.board_sharpness,
            metrics.rotation_degrees,
        )
        corner_arrays[relative] = corners

        if metrics.board_area_ratio < config.min_board_area:
            image.reasons.append(
                _reason(
                    ReasonCode.BOARD_TOO_SMALL,
                    Severity.ERROR,
                    "Detected board occupies too little of the image.",
                    metrics.board_area_ratio,
                    config.min_board_area,
                )
            )
        elif metrics.board_area_ratio > config.max_board_area:
            image.reasons.append(
                _reason(
                    ReasonCode.BOARD_TOO_LARGE,
                    Severity.ERROR,
                    "Detected board occupies too much of the image.",
                    metrics.board_area_ratio,
                    config.max_board_area,
                )
            )
        if metrics.border_distance_ratio < config.near_border_ratio:
            image.reasons.append(
                _reason(
                    ReasonCode.BOARD_CLIPPED_OR_NEAR_BORDER,
                    Severity.WARNING,
                    "Outermost detected corners are close to an image border.",
                    metrics.border_distance_ratio,
                    config.near_border_ratio,
                )
            )
        if config.min_sharpness is not None:
            metrics.sharpness_decision_source = "user_threshold"
            if metrics.board_sharpness < config.min_sharpness:
                image.reasons.append(
                    _reason(
                        ReasonCode.LOW_SHARPNESS,
                        Severity.ERROR,
                        "Board-region sharpness is below the configured threshold.",
                        metrics.board_sharpness,
                        config.min_sharpness,
                    )
                )
        if metrics.mean_intensity < 30 or metrics.near_black_ratio > 0.40:
            image.reasons.append(
                _reason(
                    ReasonCode.EXPOSURE_TOO_DARK,
                    Severity.WARNING,
                    "Image may be underexposed.",
                    metrics.mean_intensity,
                    "mean < 30 or near-black ratio > 0.40",
                )
            )
        if metrics.mean_intensity > 225 or metrics.near_white_ratio > 0.40:
            image.reasons.append(
                _reason(
                    ReasonCode.EXPOSURE_TOO_BRIGHT,
                    Severity.WARNING,
                    "Image may be overexposed.",
                    metrics.mean_intensity,
                    "mean > 225 or near-white ratio > 0.40",
                )
            )
        results.append(image)

    if not resolution_groups:
        raise DatasetValidationError("No readable supported images remain after decoding")
    if len(resolution_groups) != 1:
        groups = "; ".join(
            f"{width}x{height}: {', '.join(names)}"
            for (width, height), names in sorted(resolution_groups.items())
        )
        raise DatasetValidationError(f"Mixed image resolutions are not supported. Groups: {groups}")

    if config.min_sharpness is None:
        _apply_relative_sharpness(results, config.relative_sharpness_factor)
    _apply_duplicates(results, config)
    _finalize_states(results)
    accepted = _usable(results)
    if len(accepted) < config.min_valid_images:
        raise InsufficientViewsError(
            f"Only {len(accepted)} accepted views remain; "
            f"at least {config.min_valid_images} are required."
        )

    image_size = next(iter(resolution_groups))
    accepted_corners = [corner_arrays[image.relative_path] for image in accepted]
    calibration, reprojections = calibrate(accepted_corners, config.pattern, image_size)
    for image, stats in zip(accepted, reprojections):
        image.reprojection = stats
        if config.max_per_view_error is not None and stats.rmse_px > config.max_per_view_error:
            image.reasons.append(
                _reason(
                    ReasonCode.HIGH_REPROJECTION_ERROR,
                    Severity.WARNING,
                    "Per-view reprojection RMSE exceeds the configured quality gate.",
                    stats.rmse_px,
                    config.max_per_view_error,
                )
            )
    _finalize_states(results)

    occupancy, coverage_ratio, density = coverage_metrics(
        [image.metrics for image in accepted],
        cols=config.coverage_cols,
        rows=config.coverage_rows,
        corners=[image.corners for image in accepted],
        image_size=image_size,
    )
    scale_min, scale_max, scale_med, scale_iqr, scale_bins, rotation_range, h_range, v_range = (
        _diversity(accepted)
    )
    warnings: list[AuditReason] = []
    if coverage_ratio < config.min_coverage_ratio:
        warnings.append(
            _reason(
                ReasonCode.LOW_FIELD_COVERAGE,
                Severity.WARNING,
                "Accepted board centers cover too few image-plane grid cells.",
                coverage_ratio,
                config.min_coverage_ratio,
            )
        )
    if scale_bins < config.min_scale_bins:
        warnings.append(
            _reason(
                ReasonCode.LOW_SCALE_DIVERSITY,
                Severity.WARNING,
                "Accepted views occupy too few board-scale bins.",
                scale_bins,
                config.min_scale_bins,
            )
        )
    if rotation_range is not None and rotation_range < config.min_rotation_range_degrees:
        warnings.append(
            _reason(
                ReasonCode.LOW_POSE_DIVERSITY,
                Severity.WARNING,
                "Accepted board rotations are concentrated in a narrow range.",
                rotation_range,
                config.min_rotation_range_degrees,
            )
        )

    high_errors = sum(
        1
        for image in accepted
        if image.reprojection is not None
        and config.max_per_view_error is not None
        and image.reprojection.rmse_px > config.max_per_view_error
    )
    gates = [
        QualityGateResult(
            name="minimum_valid_images",
            passed=True,
            message=f"{len(accepted)} accepted views meet the minimum.",
            measured_value=len(accepted),
            threshold=config.min_valid_images,
        )
    ]
    if config.max_per_view_error is not None:
        gates.append(
            QualityGateResult(
                name="maximum_per_view_reprojection_error",
                passed=high_errors == 0,
                message=(
                    "All views meet the reprojection threshold."
                    if high_errors == 0
                    else f"{high_errors} view(s) exceed the reprojection threshold."
                ),
                measured_value=max(item.rmse_px for item in reprojections),
                threshold=config.max_per_view_error,
            )
        )
    if config.fail_on_warning:
        warning_count = len(warnings) + sum(
            1
            for image in results
            for reason in image.reasons
            if reason.severity == Severity.WARNING
        )
        gates.append(
            QualityGateResult(
                name="fail_on_warning",
                passed=warning_count == 0,
                message=f"{warning_count} warning(s) were produced.",
                measured_value=warning_count,
                threshold=0,
            )
        )

    accepted_count = len(accepted)
    dataset_metrics = DatasetMetrics(
        discovered_count=len(results),
        readable_count=sum(image.read_success for image in results),
        detected_count=sum(image.detection_success for image in results),
        accepted_count=accepted_count,
        warning_count=sum(image.state == ImageState.WARNING for image in results),
        rejected_count=sum(image.state == ImageState.REJECTED for image in results),
        unreadable_count=sum(image.state == ImageState.UNREADABLE for image in results),
        detection_rate=(
            sum(image.detection_success for image in results)
            / max(1, sum(image.read_success for image in results))
        ),
        coverage_grid=occupancy,
        occupied_coverage_cells=sum(value > 0 for row in occupancy for value in row),
        coverage_ratio=coverage_ratio,
        corner_density_grid=density,
        scale_min=scale_min,
        scale_max=scale_max,
        scale_median=scale_med,
        scale_iqr=scale_iqr,
        occupied_scale_bins=scale_bins,
        rotation_range_degrees=rotation_range,
        horizontal_perspective_range=h_range,
        vertical_perspective_range=v_range,
        duplicate_count=sum(image.duplicate_of is not None for image in results),
    )

    from . import __version__

    configuration = config.model_dump(mode="json", exclude={"image_directory", "output"})
    result = AuditResult(
        tool_version=__version__,
        generated_at=datetime.now().astimezone().isoformat(),
        input_directory=".",
        configuration=configuration,
        pattern=config.pattern,
        dataset_metrics=dataset_metrics,
        quality_gates=gates,
        calibration=calibration,
        images=results,
        warnings=warnings,
    )
    result._bind_source_directory(directory)
    return result

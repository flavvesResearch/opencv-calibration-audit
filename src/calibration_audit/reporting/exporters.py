"""JSON, CSV, YAML, text, image, and offline HTML exporters."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import cv2
import jinja2
import numpy as np
import yaml

from ..exceptions import DatasetValidationError, OutputExistsError
from ..io import load_image, validate_output_location
from ..models import AuditResult, ImageState

_HTML_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Calibration Audit Report</title><style>
body{font:15px system-ui,sans-serif;margin:0;color:#18212b;background:#f4f7fa}
main{max-width:1100px;margin:auto;padding:28px}section{background:white;padding:20px;margin:16px 0;border-radius:10px}
h1,h2{margin-top:0}.pass{color:#087f5b}.fail,.rejected,.unreadable{color:#c92a2a}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}
code{white-space:pre-wrap}img{max-width:100%;height:auto}.warning{color:#e67700}
.bar-row{display:grid;grid-template-columns:180px 1fr 90px;gap:10px;align-items:center;margin:7px 0}
.bar-track{height:12px;background:#e9ecef;border-radius:6px;overflow:hidden}.bar-fill{height:100%;background:#1971c2}
.image-preview{width:240px;border-radius:6px;background:#e9ecef}.preview-missing{width:220px;padding:36px 10px;background:#e9ecef;text-align:center}
.image-row.rejected,.image-row.unreadable{background:#fff5f5}.image-row.warning{background:#fff9db}
.decision{font-weight:700}.reason{margin:0 0 8px}.reason-error strong{color:#c92a2a}.reason-warning strong{color:#e67700}
.severity{font-size:11px;border:1px solid currentColor;border-radius:3px;padding:1px 4px}
</style></head><body><main>
<h1>OpenCV Calibration Audit</h1>
<section><h2>Executive summary</h2><p class="{{ 'pass' if passed else 'fail' }}">
Quality gates: {{ 'PASSED' if passed else 'FAILED' }}</p>
<p>{{ metrics.accepted_count }} accepted calibration views from {{ metrics.discovered_count }} files.
OpenCV RMS: {{ '%.5f'|format(calibration.opencv_rms) }} px.</p></section>
<section><h2>Pass/fail quality gates</h2><ul>{% for gate in gates %}
<li class="{{ 'pass' if gate.passed else 'fail' }}">{{ gate.name }} — {{ gate.message }}</li>{% endfor %}</ul></section>
<section><h2>Dataset counts and metrics</h2><pre><code>{{ metrics_json }}</code></pre></section>
<section><h2>Coverage heatmap</h2><img alt="Coverage heatmap" src="data:image/png;base64,{{ coverage }}"></section>
<section><h2>Sharpness distribution</h2>
<p>Board-region variance of Laplacian for calibration views.</p>{% for bar in sharpness_bars %}
<div class="bar-row"><span>{{ bar.label }}</span><span class="bar-track"><span class="bar-fill"
style="display:block;width:{{ bar.percent }}%"></span></span><span>{{ '%.2f'|format(bar.value) }}</span></div>
{% endfor %}</section>
<section><h2>Scale and pose diversity</h2><ul>
<li>Board area: min {{ metrics.scale_min }}, median {{ metrics.scale_median }}, max {{ metrics.scale_max }}</li>
<li>Occupied scale bins: {{ metrics.occupied_scale_bins }}</li>
<li>Rotation range: {{ metrics.rotation_range_degrees }}°</li>
<li>Perspective ranges: horizontal {{ metrics.horizontal_perspective_range }},
vertical {{ metrics.vertical_perspective_range }}</li></ul>
<p>These assessments are heuristic, not a physical certificate.</p></section>
<section><h2>Calibration parameters</h2><pre><code>{{ calibration_json }}</code></pre></section>
<section><h2>Reprojection-error chart</h2><img alt="Per-view reprojection errors" src="data:image/png;base64,{{ errors }}"></section>
<section><h2>Accepted, warning, and rejected images</h2>
<p>Annotated previews show detected inner corners and the evaluated physical board boundary.</p>
<table><thead><tr><th>Preview</th><th>Image and decision</th><th>Metrics</th><th>Decision details</th>
</tr></thead><tbody>{% for row in image_rows %}{% set image = row.image %}
<tr class="{{ image.state.value|lower }} image-row"><td>
{% if row.preview %}<img class="image-preview" alt="Annotated preview for {{ image.relative_path }}"
src="data:image/jpeg;base64,{{ row.preview }}">{% else %}
<div class="preview-missing">Preview unavailable</div>{% endif %}</td>
<td><strong>{{ image.relative_path }}</strong><br><span>{{ image.state.value }}</span><br>
<span class="decision">{{ row.decision_stage }}</span><br>Detector: {{ image.detection_method or 'n/a' }}</td>
<td>Physical board area: {{ image.metrics.board_area_ratio if image.metrics.board_area_ratio is not none else 'n/a' }}<br>
Board sharpness: {{ image.metrics.board_sharpness if image.metrics.board_sharpness is not none else 'n/a' }}<br>
In-sample RMSE: {{ image.reprojection.rmse_px if image.reprojection else 'n/a' }}</td>
<td>{% if image.reasons %}<ul>{% for reason in image.reasons %}
<li class="reason reason-{{ reason.severity.value|lower }}"><strong>{{ reason.code.value }}</strong>
<span class="severity">{{ reason.severity.value }}</span><br>{{ reason.message }}<br>
Measured: <code>{{ reason.measured_value if reason.measured_value is not none else 'n/a' }}</code>;
Threshold/rule: <code>{{ reason.threshold if reason.threshold is not none else 'n/a' }}</code></li>
{% endfor %}</ul>{% else %}No warnings or rejection reasons.{% endif %}</td></tr>
{% endfor %}</tbody></table></section>
<section><h2>Configuration and tool version</h2><p>Version {{ tool_version }}; generated {{ generated_at }}</p>
<pre><code>{{ configuration_json }}</code></pre></section>
<section><h2>Metric limitations</h2><p>Sharpness depends on resolution, optics, and target scale.
Coverage and diversity thresholds are heuristics. Per-view reprojection error is an in-sample residual:
it is calculated after fitting the camera model on the same accepted dataset and is not independent validation.
Calibration results apply only to the accepted dataset and pinhole model.</p></section>
</main></body></html>"""

_MANIFEST_NAME = "report-manifest.json"
_LEGACY_THUMBNAIL = re.compile(r"^[0-9]{4}\.jpg$")


def _png_bytes(image: np.ndarray[Any, Any]) -> bytes:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("OpenCV could not encode report chart")
    return encoded.tobytes()


def _heatmap(result: AuditResult) -> bytes:
    grid = np.asarray(result.dataset_metrics.coverage_grid, dtype=np.float32)
    maximum = float(np.max(grid)) if grid.size else 0.0
    normalized = np.zeros_like(grid, dtype=np.uint8)
    if maximum > 0:
        normalized = np.asarray(grid * (255.0 / maximum), dtype=np.uint8)
    colored = cv2.applyColorMap(normalized, cv2.COLORMAP_VIRIDIS)
    return _png_bytes(cv2.resize(colored, (640, 360), interpolation=cv2.INTER_NEAREST))


def _error_chart(result: AuditResult) -> bytes:
    values = [
        image.reprojection.rmse_px
        for image in result.images
        if image.reprojection is not None
    ]
    canvas = np.full((360, 800, 3), 255, dtype=np.uint8)
    cv2.putText(canvas, "Per-view reprojection RMSE (px)", (20, 28), 0, 0.7, (30, 30, 30), 2)
    if values:
        top = max(values) * 1.1 or 1.0
        bar_width = max(1, 740 // len(values))
        for index, value in enumerate(values):
            height = int((value / top) * 280)
            left = 30 + index * bar_width
            cv2.rectangle(
                canvas,
                (left, 330 - height),
                (left + max(1, bar_width - 2), 330),
                (190, 100, 20),
                -1,
            )
    return _png_bytes(canvas)


def _calibration_yaml(result: AuditResult) -> dict[str, Any]:
    calibration = result.calibration
    return {
        "schema_version": result.schema_version,
        "image_width": calibration.image_size[0],
        "image_height": calibration.image_size[1],
        "camera_model": calibration.camera_model,
        "camera_matrix": {
            "rows": 3,
            "cols": 3,
            "data": [value for row in calibration.camera_matrix for value in row],
        },
        "distortion_coefficients": {
            "rows": 1,
            "cols": len(calibration.distortion_coefficients),
            "data": calibration.distortion_coefficients,
        },
        "opencv_rms": calibration.opencv_rms,
        "mean_per_view_rmse_px": calibration.mean_per_view_rmse_px,
        "pattern": result.pattern.model_dump(mode="json"),
    }


def _sharpness_bars(result: AuditResult) -> list[dict[str, float | str]]:
    values = [
        (image.relative_path, image.metrics.board_sharpness)
        for image in result.images
        if image.metrics.board_sharpness is not None
        and image.state in (ImageState.ACCEPTED, ImageState.WARNING)
    ]
    maximum = max((value for _, value in values), default=1.0)
    return [
        {
            "label": label,
            "value": value,
            "percent": min(100.0, max(0.0, value / maximum * 100.0)),
        }
        for label, value in values
    ]


def _safe_managed_path(output: Path, relative_path: str) -> Path | None:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    candidate = output / relative
    try:
        candidate.resolve().relative_to(output.resolve())
    except (DatasetValidationError, OSError, ValueError):
        return None
    return candidate


def _remove_previous_managed_files(output: Path) -> None:
    """Remove files declared by the prior manifest plus legacy numbered previews."""

    manifest = output / _MANIFEST_NAME
    if manifest.is_file():
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            generated = payload.get("generated_files", [])
        except (OSError, json.JSONDecodeError, AttributeError):
            generated = []
        if isinstance(generated, list):
            for relative_path in generated:
                if not isinstance(relative_path, str):
                    continue
                candidate = _safe_managed_path(output, relative_path)
                if candidate is not None and (candidate.is_file() or candidate.is_symlink()):
                    candidate.unlink()

    legacy_directory = output / "assets" / "thumbnails"
    if legacy_directory.is_dir():
        for candidate in legacy_directory.iterdir():
            if candidate.is_file() and _LEGACY_THUMBNAIL.fullmatch(candidate.name):
                candidate.unlink()


def _decision_stage(image_state: ImageState, reason_codes: set[str]) -> str:
    if image_state in (ImageState.REJECTED, ImageState.UNREADABLE):
        return "Rejected before calibration"
    if "HIGH_REPROJECTION_ERROR" in reason_codes:
        return "Flagged after calibration"
    if image_state == ImageState.WARNING:
        return "Accepted with warning"
    return "Accepted for calibration"


def _annotated_preview(
    result: AuditResult, relative_path: str, corners: list[list[float]], boundary: list[list[float]] | None
) -> bytes | None:
    source = result.source_directory / relative_path
    try:
        source.resolve().relative_to(result.source_directory.resolve())
        maximum = int(result.configuration.get("max_file_size_mb", 100)) * 1024 * 1024
        analysis, _, channels, _, _ = load_image(source, max_file_size_bytes=maximum)
    except (DatasetValidationError, OSError, ValueError):
        return None
    if channels == 1:
        preview = cv2.cvtColor(analysis, cv2.COLOR_GRAY2BGR)
    elif channels == 4:
        preview = cv2.cvtColor(analysis, cv2.COLOR_BGRA2BGR)
    else:
        preview = analysis.copy()
    height, width = preview.shape[:2]
    if boundary:
        polygon = np.asarray(boundary, dtype=np.float64)
        polygon[:, 0] = np.clip(polygon[:, 0], 0, max(0, width - 1))
        polygon[:, 1] = np.clip(polygon[:, 1], 0, max(0, height - 1))
        cv2.polylines(
            preview,
            [polygon.astype(np.int32)],
            isClosed=True,
            color=(255, 0, 255),
            thickness=3,
            lineType=cv2.LINE_AA,
        )
    for x, y in corners:
        point = (
            int(np.clip(x, 0, max(0, width - 1))),
            int(np.clip(y, 0, max(0, height - 1))),
        )
        cv2.circle(preview, point, 3, (255, 255, 0), -1, lineType=cv2.LINE_AA)
    scale = min(1.0, 320.0 / max(width, height, 1))
    thumbnail = cv2.resize(
        preview,
        (max(1, int(width * scale)), max(1, int(height * scale))),
        interpolation=cv2.INTER_AREA,
    )
    success, encoded = cv2.imencode(".jpg", thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return encoded.tobytes() if success else None


def write_outputs(result: AuditResult, output_directory: Path, *, overwrite: bool = False) -> None:
    """Write the complete deterministic output set."""

    output = Path(output_directory)
    validate_output_location(
        result.source_directory,
        output,
        recursive=bool(result.configuration.get("recursive", False)),
    )
    if output.exists() and not output.is_dir():
        raise OutputExistsError(f"Output path is not a directory: {output}")
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise OutputExistsError(
            f"Output directory is not empty: {output}. Use overwrite=True or --overwrite-output."
        )
    if output.exists() and overwrite:
        _remove_previous_managed_files(output)
    assets = output / "assets"
    thumbnails = assets / "thumbnails"
    thumbnails.mkdir(parents=True, exist_ok=True)

    payload = result.model_dump(mode="json")
    payload["passed"] = result.passed
    (output / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output / "calibration.yaml").write_text(
        yaml.safe_dump(_calibration_yaml(result), sort_keys=False), encoding="utf-8"
    )

    fieldnames = [
        "relative_path",
        "read_success",
        "resolution",
        "detection_success",
        "detection_method",
        "original_dtype",
        "original_bit_depth",
        "global_sharpness",
        "board_sharpness",
        "board_center_x",
        "board_center_y",
        "board_area_ratio",
        "rotation_degrees",
        "horizontal_perspective",
        "vertical_perspective",
        "duplicate_of",
        "final_state",
        "reason_codes",
        "reprojection_rmse_px",
    ]
    with (output / "images.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for image in result.images:
            center = image.metrics.board_center
            writer.writerow(
                {
                    "relative_path": image.relative_path,
                    "read_success": image.read_success,
                    "resolution": (
                        f"{image.metrics.width}x{image.metrics.height}"
                        if image.metrics.width is not None
                        else ""
                    ),
                    "detection_success": image.detection_success,
                    "detection_method": image.detection_method or "",
                    "original_dtype": image.metrics.original_dtype or "",
                    "original_bit_depth": image.metrics.original_bit_depth or "",
                    "global_sharpness": image.metrics.global_sharpness,
                    "board_sharpness": image.metrics.board_sharpness,
                    "board_center_x": center[0] if center else "",
                    "board_center_y": center[1] if center else "",
                    "board_area_ratio": image.metrics.board_area_ratio,
                    "rotation_degrees": image.metrics.rotation_degrees,
                    "horizontal_perspective": image.metrics.horizontal_perspective,
                    "vertical_perspective": image.metrics.vertical_perspective,
                    "duplicate_of": image.duplicate_of or "",
                    "final_state": image.state.value,
                    "reason_codes": "|".join(reason.code.value for reason in image.reasons),
                    "reprojection_rmse_px": (
                        image.reprojection.rmse_px if image.reprojection else ""
                    ),
                }
            )

    accepted = [
        image.relative_path
        for image in result.images
        if image.state in (ImageState.ACCEPTED, ImageState.WARNING)
    ]
    rejected = [
        image.relative_path
        for image in result.images
        if image.state in (ImageState.REJECTED, ImageState.UNREADABLE)
    ]
    (output / "accepted.txt").write_text(
        "".join(f"{path}\n" for path in accepted), encoding="utf-8"
    )
    (output / "rejected.txt").write_text(
        "".join(f"{path}\n" for path in rejected), encoding="utf-8"
    )

    heatmap = _heatmap(result)
    errors = _error_chart(result)
    (assets / "coverage_heatmap.png").write_bytes(heatmap)
    (assets / "reprojection_errors.png").write_bytes(errors)
    generated_files = {
        "accepted.txt",
        "assets/coverage_heatmap.png",
        "assets/reprojection_errors.png",
        "calibration.yaml",
        "images.csv",
        "rejected.txt",
        "report.html",
        _MANIFEST_NAME,
        "summary.json",
    }
    image_rows: list[dict[str, Any]] = []
    for image_result in result.images:
        preview = None
        if image_result.read_success:
            preview_bytes = _annotated_preview(
                result,
                image_result.relative_path,
                image_result.corners,
                image_result.metrics.board_boundary,
            )
            if preview_bytes is not None:
                identifier = hashlib.sha256(
                    image_result.relative_path.encode("utf-8")
                ).hexdigest()[:20]
                relative_thumbnail = f"assets/thumbnails/{identifier}.jpg"
                (output / relative_thumbnail).write_bytes(preview_bytes)
                generated_files.add(relative_thumbnail)
                preview = base64.b64encode(preview_bytes).decode("ascii")
        image_rows.append(
            {
                "image": image_result,
                "preview": preview,
                "decision_stage": _decision_stage(
                    image_result.state,
                    {reason.code.value for reason in image_result.reasons},
                ),
            }
        )
    environment = jinja2.Environment(autoescape=True)
    template = environment.from_string(_HTML_TEMPLATE)
    html = template.render(
        passed=result.passed,
        metrics=result.dataset_metrics,
        calibration=result.calibration,
        gates=result.quality_gates,
        image_rows=image_rows,
        tool_version=result.tool_version,
        generated_at=result.generated_at,
        metrics_json=json.dumps(result.dataset_metrics.model_dump(mode="json"), indent=2),
        calibration_json=json.dumps(result.calibration.model_dump(mode="json"), indent=2),
        configuration_json=json.dumps(result.configuration, indent=2),
        coverage=base64.b64encode(heatmap).decode("ascii"),
        errors=base64.b64encode(errors).decode("ascii"),
        sharpness_bars=_sharpness_bars(result),
    )
    (output / "report.html").write_text(html, encoding="utf-8")
    (output / _MANIFEST_NAME).write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "generated_files": sorted(generated_files),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

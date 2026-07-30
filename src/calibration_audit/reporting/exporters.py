"""JSON, CSV, YAML, text, image, and offline HTML exporters."""

from __future__ import annotations

import base64
import csv
import json
from pathlib import Path
from typing import Any

import cv2
import jinja2
import numpy as np
import yaml

from ..exceptions import OutputExistsError
from ..models import AuditResult, ImageState

_HTML_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Calibration Audit Report</title><style>
body{font:15px system-ui,sans-serif;margin:0;color:#18212b;background:#f4f7fa}
main{max-width:1100px;margin:auto;padding:28px}section{background:white;padding:20px;margin:16px 0;border-radius:10px}
h1,h2{margin-top:0}.pass{color:#087f5b}.fail,.rejected,.unreadable{color:#c92a2a}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px;border-bottom:1px solid #ddd;text-align:left}
code{white-space:pre-wrap}img{max-width:100%;height:auto}.warning{color:#e67700}
.bar-row{display:grid;grid-template-columns:180px 1fr 90px;gap:10px;align-items:center;margin:7px 0}
.bar-track{height:12px;background:#e9ecef;border-radius:6px;overflow:hidden}.bar-fill{height:100%;background:#1971c2}
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
<section><h2>Accepted, warning, and rejected images</h2><table><thead><tr>
<th>Image</th><th>State</th><th>Detector</th><th>Board area</th><th>Sharpness</th><th>RMSE</th><th>Reasons</th>
</tr></thead><tbody>{% for image in images %}<tr><td>{{ image.relative_path }}</td>
<td class="{{ image.state.value|lower }}">{{ image.state.value }}</td><td>{{ image.detection_method or '' }}</td>
<td>{{ image.metrics.board_area_ratio if image.metrics.board_area_ratio is not none else '' }}</td>
<td>{{ image.metrics.board_sharpness if image.metrics.board_sharpness is not none else '' }}</td>
<td>{{ image.reprojection.rmse_px if image.reprojection else '' }}</td>
<td>{{ image.reasons|map(attribute='code.value')|join(', ') }}</td></tr>{% endfor %}</tbody></table></section>
<section><h2>Configuration and tool version</h2><p>Version {{ tool_version }}; generated {{ generated_at }}</p>
<pre><code>{{ configuration_json }}</code></pre></section>
<section><h2>Metric limitations</h2><p>Sharpness depends on resolution, optics, and target scale.
Coverage and diversity thresholds are heuristics. Calibration results apply only to the accepted dataset and pinhole model.</p></section>
</main></body></html>"""


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


def write_outputs(result: AuditResult, output_directory: Path, *, overwrite: bool = False) -> None:
    """Write the complete deterministic output set."""

    output = Path(output_directory)
    if output.exists() and not output.is_dir():
        raise OutputExistsError(f"Output path is not a directory: {output}")
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise OutputExistsError(
            f"Output directory is not empty: {output}. Use overwrite=True or --overwrite-output."
        )
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
    input_root = result.source_directory
    try:
        resolved_input_root = input_root.resolve()
    except OSError:
        resolved_input_root = input_root
    for index, image_result in enumerate(result.images):
        if not image_result.read_success:
            continue
        source = input_root / image_result.relative_path
        try:
            source.resolve().relative_to(resolved_input_root)
            encoded_source = np.fromfile(source, dtype=np.uint8)
            source_image = cv2.imdecode(encoded_source, cv2.IMREAD_COLOR)
        except (OSError, ValueError):
            source_image = None
        if source_image is None:
            continue
        height, width = source_image.shape[:2]
        scale = min(1.0, 240.0 / max(width, 1))
        thumbnail = cv2.resize(
            source_image,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
        success, encoded_thumbnail = cv2.imencode(".jpg", thumbnail)
        if success:
            (thumbnails / f"{index:04d}.jpg").write_bytes(encoded_thumbnail.tobytes())
    environment = jinja2.Environment(autoescape=True)
    template = environment.from_string(_HTML_TEMPLATE)
    html = template.render(
        passed=result.passed,
        metrics=result.dataset_metrics,
        calibration=result.calibration,
        gates=result.quality_gates,
        images=result.images,
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

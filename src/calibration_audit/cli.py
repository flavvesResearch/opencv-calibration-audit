"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pydantic import ValidationError

from . import __version__
from .config import AuditConfig
from .exceptions import (
    CalibrationAuditError,
    DatasetValidationError,
    InvalidConfigurationError,
    OutputExistsError,
)
from .models import PatternSpec
from .pipeline import audit_dataset

log = logging.getLogger(__name__)


def _get_version() -> str:
    return f"calibration-audit version {__version__}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a checkerboard calibration dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=_get_version())
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze, calibrate, and report on checkerboard images.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    analyze.add_argument("image_directory", type=Path)
    analyze.add_argument("--cols", type=int, required=True, help="Inner corners horizontally.")
    analyze.add_argument("--rows", type=int, required=True, help="Inner corners vertically.")
    analyze.add_argument("--square-size", type=float, required=True)
    analyze.add_argument("--unit", choices=["mm", "cm", "inch", "m"], default="mm")
    analyze.add_argument(
        "--output",
        type=Path,
        default=Path("./calibration-audit-output"),
        help="Report directory; must be outside the input tree with --recursive.",
    )
    analyze.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subdirectories; rejects an output directory inside the input tree.",
    )
    analyze.add_argument("--min-valid-images", type=int, default=10)
    analyze.add_argument("--min-board-area", type=float, default=0.03)
    analyze.add_argument("--max-board-area", type=float, default=0.90)
    analyze.add_argument("--min-sharpness", type=float)
    analyze.add_argument("--max-per-view-error", type=float)
    analyze.add_argument("--disable-fallback-detector", action="store_true")
    analyze.add_argument("--fail-on-warning", action="store_true")
    analyze.add_argument("--overwrite-output", action="store_true")
    analyze.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    )
    return parser


def _run(args: argparse.Namespace) -> int:
    pattern = PatternSpec(
        cols=args.cols,
        rows=args.rows,
        square_size=args.square_size,
        unit=args.unit,
    )
    config = AuditConfig(
        pattern=pattern,
        output=args.output,
        recursive=args.recursive,
        min_valid_images=args.min_valid_images,
        min_board_area=args.min_board_area,
        max_board_area=args.max_board_area,
        min_sharpness=args.min_sharpness,
        max_per_view_error=args.max_per_view_error,
        disable_fallback_detector=args.disable_fallback_detector,
        fail_on_warning=args.fail_on_warning,
        overwrite_output=args.overwrite_output,
        log_level=args.log_level,
    )
    result = audit_dataset(args.image_directory, config)
    result.write_outputs(args.output, overwrite=args.overwrite_output)
    log.info(
        "Audit complete: %d accepted views; report: %s",
        result.dataset_metrics.accepted_count,
        args.output / "report.html",
    )
    print(
        f"Quality gates: {'PASSED' if result.passed else 'FAILED'}\n"
        f"Accepted views: {result.dataset_metrics.accepted_count}\n"
        f"OpenCV RMS: {result.calibration.opencv_rms:.6f} px\n"
        f"Report: {args.output / 'report.html'}"
    )
    return 0 if result.passed else 1


def main() -> None:
    """CLI entry point; library code raises exceptions and never exits."""

    parser = build_parser()
    args = parser.parse_args()
    level = getattr(logging, getattr(args, "log_level", "INFO"))
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", force=True)
    try:
        raise SystemExit(_run(args))
    except ValidationError as exc:
        log.error("Configuration error:\n%s", exc)
        raise SystemExit(2) from None
    except (InvalidConfigurationError, DatasetValidationError, OutputExistsError) as exc:
        log.error("%s", exc)
        raise SystemExit(2) from None
    except CalibrationAuditError as exc:
        log.error("Processing failed: %s", exc, exc_info=level == logging.DEBUG)
        raise SystemExit(3) from None
    except Exception as exc:
        log.error("Unexpected processing failure: %s", exc, exc_info=level == logging.DEBUG)
        raise SystemExit(3) from None


if __name__ == "__main__":
    main()

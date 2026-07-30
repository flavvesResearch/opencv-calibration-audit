"""Command-line interface for the calibration audit tool."""

import argparse
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from . import __version__
from .config import AuditConfig
from .exceptions import CalibrationAuditError, InvalidConfigurationError
from .models import PatternSpec

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _get_version() -> str:
    """Returns the package version."""
    return f"calibration-audit version {__version__}"


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Audit a checkerboard calibration dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Main command
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze a dataset of calibration images."
    )

    # Required arguments for analyze
    analyze_parser.add_argument(
        "image_directory",
        type=Path,
        help="Path to the directory containing calibration images.",
    )
    analyze_parser.add_argument(
        "--cols", type=int, required=True, help="Number of inner corners horizontally."
    )
    analyze_parser.add_argument(
        "--rows", type=int, required=True, help="Number of inner corners vertically."
    )
    analyze_parser.add_argument(
        "--square-size", type=float, required=True, help="Size of a checkerboard square."
    )

    # Optional arguments for analyze
    analyze_parser.add_argument(
        "--unit",
        type=str,
        default="mm",
        choices=["mm", "cm", "inch", "m"],
        help="Unit for square size.",
    )
    analyze_parser.add_argument(
        "--output",
        type=Path,
        default=Path("./calibration-audit-output"),
        help="Output directory for reports.",
    )
    analyze_parser.add_argument(
        "--recursive", action="store_true", help="Recursively search for images."
    )
    analyze_parser.add_argument(
        "--min-valid-images",
        type=int,
        default=10,
        help="Minimum number of valid images to proceed.",
    )
    analyze_parser.add_argument(
        "--min-board-area",
        type=float,
        default=0.03,
        help="Minimum board area as a fraction of image area.",
    )
    analyze_parser.add_argument(
        "--max-board-area",
        type=float,
        default=0.90,
        help="Maximum board area as a fraction of image area.",
    )
    analyze_parser.add_argument(
        "--min-sharpness", type=float, help="Absolute minimum sharpness threshold."
    )
    analyze_parser.add_argument(
        "--max-per-view-error",
        type=float,
        help="Maximum per-view reprojection error for quality gate.",
    )
    analyze_parser.add_argument(
        "--disable-fallback-detector",
        action="store_true",
        help="Disable fallback corner detector.",
    )
    analyze_parser.add_argument(
        "--fail-on-warning", action="store_true", help="Return a failure exit code on any warning."
    )
    analyze_parser.add_argument(
        "--overwrite-output", action="store_true", help="Allow overwriting output directory."
    )
    analyze_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level.",
    )

    # Version argument for root parser
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=_get_version(),
        help="Show the version and exit.",
    )

    args = parser.parse_args()

    # Set log level from args
    log.setLevel(args.log_level)

    try:
        if args.command == "analyze":
            pattern_spec = PatternSpec(
                cols=args.cols,
                rows=args.rows,
                square_size=args.square_size,
                unit=args.unit,
            )

            config = AuditConfig(
                image_directory=args.image_directory,
                pattern=pattern_spec,
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

            log.info("Phase 1: Configuration loaded successfully.")
            log.debug(config.model_dump_json(indent=2))

            # In later phases, the main processing function will be called here.
            # For now, we just demonstrate that configuration is built.
            print("\nConfiguration:")
            print(config.model_dump_json(indent=2))

            sys.exit(0)

    except ValidationError as e:
        log.error(f"Configuration error:\n{e}")
        sys.exit(2)  # Exit code 2 for invalid arguments
    except InvalidConfigurationError as e:
        log.error(f"Configuration error: {e}")
        sys.exit(2)
    except CalibrationAuditError as e:
        log.error(f"An error occurred: {e}")
        sys.exit(3)  # Exit code 3 for unexpected runtime error
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=log.level == logging.DEBUG)
        sys.exit(3)


if __name__ == "__main__":
    main()
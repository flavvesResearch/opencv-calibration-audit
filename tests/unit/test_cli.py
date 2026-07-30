"""Unit tests for the command-line interface."""

import sys
from unittest.mock import patch

import pytest
from _pytest.capture import CaptureFixture
from _pytest.logging import LogCaptureFixture

from calibration_audit.cli import main


def run_cli(*args: str) -> None:
    """Helper function to run the CLI with mocked sys.argv."""
    with patch.object(sys, "argv", ["calibration-audit", *args]):
        main()


def test_cli_version(capsys: CaptureFixture[str]) -> None:
    """Test the --version flag."""
    with pytest.raises(SystemExit) as exc_info:
        run_cli("--version")
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "calibration-audit version" in captured.out


def test_cli_help(capsys: CaptureFixture[str]) -> None:
    """Test the --help flag."""
    with pytest.raises(SystemExit) as exc_info:
        run_cli("--help")
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: calibration-audit" in captured.out
    assert "analyze" in captured.out


def test_cli_analyze_missing_args(capsys: CaptureFixture[str]) -> None:
    """Test calling analyze with missing required arguments."""
    with pytest.raises(SystemExit) as exc_info:
        run_cli("analyze", "./images")
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "the following arguments are required: --cols, --rows, --square-size" in captured.err


def test_cli_analyze_basic_config(caplog: LogCaptureFixture) -> None:
    """Test a minimal valid call to the analyze command."""
    with pytest.raises(SystemExit) as exc_info:
        run_cli(
            "analyze",
            "./images",
            "--cols",
            "9",
            "--rows",
            "6",
            "--square-size",
            "30",
        )
    assert exc_info.value.code == 0
    assert "Configuration loaded successfully." in caplog.text


def test_cli_analyze_full_config(caplog: LogCaptureFixture) -> None:
    """Test a call with all arguments to the analyze command."""
    with pytest.raises(SystemExit) as exc_info:
        run_cli(
            "analyze",
            "/data/images",
            "--cols",
            "10",
            "--rows",
            "7",
            "--square-size",
            "25.5",
            "--unit",
            "cm",
            "--output",
            "/tmp/output",
            "--recursive",
            "--min-valid-images",
            "15",
            "--min-board-area",
            "0.05",
            "--max-board-area",
            "0.85",
            "--min-sharpness",
            "100.0",
            "--max-per-view-error",
            "0.5",
            "--disable-fallback-detector",
            "--fail-on-warning",
            "--overwrite-output",
            "--log-level",
            "DEBUG",
        )
    assert exc_info.value.code == 0
    assert "Configuration loaded successfully." in caplog.text
    assert "DEBUG" in caplog.text


def test_cli_invalid_config_value(caplog: LogCaptureFixture) -> None:
    """Test that the CLI exits with code 2 for an invalid pydantic value."""
    with pytest.raises(SystemExit) as exc_info:
        run_cli(
            "analyze",
            "./images",
            "--cols",
            "1",  # Invalid, must be >= 2
            "--rows",
            "6",
            "--square-size",
            "30",
        )
    assert exc_info.value.code == 2
    assert "Configuration error" in caplog.text
    assert "Input should be greater than or equal to 2" in caplog.text

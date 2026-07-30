"""CLI exit-code and argument handling tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from calibration_audit.cli import main
from calibration_audit.exceptions import CalibrationFailedError, DatasetValidationError


def run_cli(*args: str) -> int:
    with patch.object(sys, "argv", ["calibration-audit", *args]), pytest.raises(
        SystemExit
    ) as exc_info:
        main()
    assert isinstance(exc_info.value.code, int)
    return exc_info.value.code


def valid_args() -> tuple[str, ...]:
    return ("analyze", ".", "--cols", "9", "--rows", "6", "--square-size", "30")


def test_version_and_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli("--version") == 0
    assert "calibration-audit version" in capsys.readouterr().out
    assert run_cli("--help") == 0
    assert "analyze" in capsys.readouterr().out


def test_missing_required_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli("analyze", ".") == 2
    assert "--cols" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (DatasetValidationError("bad dataset"), 2),
        (CalibrationFailedError("opencv failed"), 3),
        (RuntimeError("unexpected"), 3),
    ],
)
def test_exception_exit_mapping(
    error: Exception, expected: int, capsys: pytest.CaptureFixture[str]
) -> None:
    with patch("calibration_audit.cli.audit_dataset", side_effect=error):
        assert run_cli(*valid_args()) == expected
    assert "Traceback" not in capsys.readouterr().err


def test_debug_mode_includes_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("calibration_audit.cli.audit_dataset", side_effect=RuntimeError("boom")):
        assert run_cli(*valid_args(), "--log-level", "DEBUG") == 3
    assert "Traceback" in capsys.readouterr().err


def test_invalid_configuration_is_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    args = list(valid_args())
    args[args.index("9")] = "1"
    assert run_cli(*args) == 2
    assert "Configuration error" in capsys.readouterr().err


def test_quality_gate_failure_is_exit_1(tmp_path: Path) -> None:
    result = Mock()
    result.passed = False
    result.dataset_metrics.accepted_count = 10
    result.calibration.opencv_rms = 0.5
    result.write_outputs.return_value = None
    with patch("calibration_audit.cli.audit_dataset", return_value=result):
        assert run_cli(*valid_args(), "--output", str(tmp_path / "out")) == 1
    result.write_outputs.assert_called_once()

from __future__ import annotations

import pytest

from kautilya.cli import main


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "kautilya" in out
    assert "validate-config" in out


def test_validate_config_passes(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["validate-config"])

    assert code == 0
    assert "config OK" in capsys.readouterr().out


def test_stub_commands_exit_two() -> None:
    assert main(["download"]) == 2
    assert main(["ask", "what is cheating"]) == 2

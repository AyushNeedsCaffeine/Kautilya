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
    assert main(["download-scj"]) == 2


def test_eval_is_now_real() -> None:
    import kautilya.cli as cli

    assert "eval" not in cli._NOT_IMPLEMENTED
    sub = cli.build_parser()._subparsers._group_actions[0].choices
    assert "eval" in sub
    helptext = sub["eval"].format_help()
    assert "--stage" in helptext and "retrieval" in helptext


def test_ask_is_now_real() -> None:
    import kautilya.cli as cli

    assert "ask" not in cli._NOT_IMPLEMENTED
    sub = cli.build_parser()._subparsers._group_actions[0].choices
    assert "ask" in sub

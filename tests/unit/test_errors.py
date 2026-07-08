"""exit code 규약 (P5.2): 0 성공 / 1 실행 실패 / 2 사용법·설정 오류."""

import pytest
from typer.testing import CliRunner

from rosmac import cli
from rosmac.errors import RosmacError, UsageError

runner = CliRunner()


def test_error_hierarchy() -> None:
    # 기존 `except RuntimeError` 방어선(psview 등)이 계속 동작해야 한다
    assert issubclass(RosmacError, RuntimeError)
    assert RosmacError("x").exit_code == 1
    assert UsageError("x").exit_code == 2


@pytest.mark.parametrize(
    ("exc", "expected"),
    [(RosmacError("실행 실패"), 1), (UsageError("사용법"), 2), (ValueError("예상 밖"), 1)],
)
def test_main_exit_codes(monkeypatch: pytest.MonkeyPatch, exc: Exception, expected: int) -> None:
    def boom() -> None:
        raise exc

    monkeypatch.setattr(cli, "app", boom)
    with pytest.raises(SystemExit) as ei:
        cli.main()
    assert ei.value.code == expected


def test_invalid_preset_is_usage_error() -> None:
    result = runner.invoke(cli.app, ["sim", "no-such-preset"])
    assert isinstance(result.exception, UsageError)
    assert result.exception.exit_code == 2


def test_push_without_src_is_usage_error(tmp_path) -> None:
    result = runner.invoke(cli.app, ["push", str(tmp_path)])
    assert isinstance(result.exception, UsageError)
    assert result.exception.exit_code == 2

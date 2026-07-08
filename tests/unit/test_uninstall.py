"""rosmac uninstall — 대상 열거·확인·제거 순서 (P5.2 ③, 절대 규칙 7)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from rosmac import cli, lima
from rosmac.config import Config

runner = CliRunner()


@pytest.fixture()
def fake_world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, list[str]]:
    """env·VM·~/.rosmac이 전부 존재하는 세계. 제거 호출을 기록한다."""
    calls: dict[str, list[str]] = {"removed": []}
    rosmac_dir = tmp_path / ".rosmac"
    rosmac_dir.mkdir()
    (rosmac_dir / "config.yaml").write_text("{}")

    monkeypatch.setattr(cli, "load", lambda: Config())
    monkeypatch.setattr(cli, "_kill_ros2_daemon", lambda: None)
    monkeypatch.setattr(cli.bridge, "stop", lambda: False)
    monkeypatch.setattr(cli.conda, "env_exists", lambda name: True)
    monkeypatch.setattr(cli.conda, "remove_env", lambda cfg: calls["removed"].append("env"))
    monkeypatch.setattr(cli.lima, "state", lambda name: lima.VmState.RUNNING)
    monkeypatch.setattr(cli.lima, "delete", lambda name: calls["removed"].append("vm"))
    monkeypatch.setattr("rosmac.config.CONFIG_PATH", rosmac_dir / "config.yaml")
    calls["rosmac_dir"] = [str(rosmac_dir)]
    return calls


def test_uninstall_yes_removes_in_order(fake_world: dict[str, list[str]]) -> None:
    result = runner.invoke(cli.app, ["uninstall", "--yes"])
    assert result.exit_code == 0
    assert fake_world["removed"] == ["env", "vm"]  # env → VM 순서
    assert not Path(fake_world["rosmac_dir"][0]).exists()  # ~/.rosmac rmtree


def test_uninstall_confirm_skips_on_no(fake_world: dict[str, list[str]]) -> None:
    result = runner.invoke(cli.app, ["uninstall"], input="n\nn\nn\n")
    assert result.exit_code == 0
    assert fake_world["removed"] == []
    assert Path(fake_world["rosmac_dir"][0]).exists()
    assert "skipped" in result.output


def test_uninstall_clean_world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "load", lambda: Config())
    monkeypatch.setattr(cli, "_kill_ros2_daemon", lambda: None)
    monkeypatch.setattr(cli.bridge, "stop", lambda: False)
    monkeypatch.setattr(cli.conda, "env_exists", lambda name: False)
    monkeypatch.setattr(cli.lima, "state", lambda name: lima.VmState.ABSENT)
    monkeypatch.setattr("rosmac.config.CONFIG_PATH", tmp_path / "nope" / "config.yaml")
    result = runner.invoke(cli.app, ["uninstall", "--yes"])
    assert result.exit_code == 0
    assert "nothing to remove" in result.output

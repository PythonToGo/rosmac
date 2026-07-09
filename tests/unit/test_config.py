from pathlib import Path

import pytest

from rosmac import config


def test_load_creates_default_when_missing(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    cfg = config.load(path)
    assert path.exists()
    assert cfg.vm.name == "rosmac"
    assert cfg.bridge.version == config.BRIDGE_VERSION
    assert cfg.ros.rmw == "rmw_cyclonedds_cpp"
    assert cfg.conda_channel == "robostack-humble"


def test_load_existing_overrides(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("vm:\n  cpus: 8\nbridge:\n  port: 7448\n")
    cfg = config.load(path)
    assert cfg.vm.cpus == 8
    assert cfg.bridge.port == 7448
    assert cfg.ros.distro == "humble"  # 나머지는 기본값 유지


def test_load_invalid_value_raises_config_error(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("vm:\n  cpus: many\n")
    with pytest.raises(config.ConfigError) as exc:
        config.load(path)
    assert "cpus" in str(exc.value)
    assert str(path) in str(exc.value)


def test_load_broken_yaml_raises_config_error(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("vm: [unclosed\n")
    with pytest.raises(config.ConfigError):
        config.load(path)


def test_robot_defaults_off(tmp_path: Path) -> None:
    """robot 미설정이면 host=None — 기존 사용자 무영향 (D15)."""
    cfg = config.load(tmp_path / "config.yaml")
    assert cfg.robot.host is None
    assert cfg.robot.port == 7447


def test_robot_host_valid(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("robot:\n  host: 192.168.1.50\n  port: 7448\n")
    cfg = config.load(path)
    assert cfg.robot.host == "192.168.1.50"
    assert cfg.robot.port == 7448


@pytest.mark.parametrize("bad", ["robot:7447", "a b", "tcp/1.2.3.4", "host;rm"])
def test_robot_host_invalid_raises_config_error(tmp_path: Path, bad: str) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(f"robot:\n  host: '{bad}'\n")
    with pytest.raises(config.ConfigError):
        config.load(path)


def test_robot_port_out_of_range(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("robot:\n  host: robot.local\n  port: 0\n")
    with pytest.raises(config.ConfigError):
        config.load(path)

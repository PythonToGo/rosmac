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

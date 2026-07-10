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


# ── E.7 업그레이드 경로: 핀 비저장·마이그레이션 ──────────────────────────


def test_fresh_config_file_has_no_pins(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    config.load(p)  # 생성
    text = p.read_text()
    for frozen in ("version:", "sha256_darwin", "sha256_linux", "rmw:", "conda_channel"):
        assert frozen not in text, frozen
    assert "port:" in text  # 핀이 아닌 값은 저장됨


def test_old_style_frozen_config_follows_code_pins(tmp_path: Path) -> None:
    # 구세대 config: 당시 기본값이 통째로 동결돼 있던 형태 (E.7 배경)
    p = tmp_path / "config.yaml"
    p.write_text(
        f"bridge:\n  port: 7447\n  version: {config.BRIDGE_VERSION}\n"
        f"  sha256_darwin: {config.BRIDGE_SHA256_DARWIN}\n"
        f"ros:\n  rmw: {config.PINNED_RMW}\nconda_channel: {config.PINNED_CHANNEL}\n"
    )
    cfg = config.load(p)
    assert cfg.bridge.version == config.BRIDGE_VERSION
    assert cfg.ros.rmw == config.PINNED_RMW


def test_pin_bump_release_scenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 릴리스 시나리오: 코드 핀이 올라가고 히스토리에 옛 값이 남은 상태에서
    # 옛 기본값이 동결된 config를 로드하면 → 신 핀을 따른다
    monkeypatch.setitem(
        config._PIN_HISTORY, ("bridge", "version"), {config.BRIDGE_VERSION, "0.9.9-old"}
    )
    p = tmp_path / "config.yaml"
    p.write_text("bridge:\n  version: 0.9.9-old\n")
    cfg = config.load(p)
    assert cfg.bridge.version == config.BRIDGE_VERSION  # 신 핀 사용


def test_custom_pin_survives_load_and_save(tmp_path: Path) -> None:
    # 역대 기본값이 아닌 값 = 사용자 명시 핀 → 로드·저장 모두 보존
    p = tmp_path / "config.yaml"
    p.write_text("bridge:\n  version: 1.8.6\n")
    cfg = config.load(p)
    assert cfg.bridge.version == "1.8.6"
    out = tmp_path / "resaved.yaml"
    config.save(cfg, out)
    assert "1.8.6" in out.read_text()

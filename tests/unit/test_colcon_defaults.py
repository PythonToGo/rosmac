"""P4.1 — colcon 기본값 주입 (KI-25) 유닛 테스트."""

import yaml

from rosmac import assets, conda
from rosmac.config import Config


def test_ensure_colcon_defaults_writes_and_is_idempotent(tmp_path, monkeypatch) -> None:
    target = tmp_path / "colcon-defaults.yaml"
    monkeypatch.setattr(assets, "COLCON_DEFAULTS_PATH", target)
    path1 = assets.ensure_colcon_defaults()
    assert path1 == str(target)
    doc = yaml.safe_load(target.read_text())
    assert "-DCMAKE_POLICY_DEFAULT_CMP0094=NEW" in doc["build"]["cmake-args"]
    mtime = target.stat().st_mtime_ns
    assert assets.ensure_colcon_defaults() == path1  # 재호출 멱등
    assert target.stat().st_mtime_ns == mtime  # 내용 동일하면 안 씀


def test_ensure_colcon_defaults_refreshes_stale_content(tmp_path, monkeypatch) -> None:
    target = tmp_path / "colcon-defaults.yaml"
    monkeypatch.setattr(assets, "COLCON_DEFAULTS_PATH", target)
    target.write_text("stale: true\n")  # 구버전 잔재 시나리오
    assets.ensure_colcon_defaults()
    assert "CMP0094" in target.read_text()


def test_ros_env_pairs_includes_colcon_defaults_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(assets, "COLCON_DEFAULTS_PATH", tmp_path / "cd.yaml")
    monkeypatch.setattr(assets, "MAC_CYCLONEDDS_PATH", tmp_path / "cyclonedds.xml")
    pairs = conda.ros_env_pairs(Config())
    keys = [p.split("=", 1)[0] for p in pairs]
    # KI-6의 5종 + KI-25의 1종이 전부 있어야 한다
    assert keys == [
        "ROS_LOCALHOST_ONLY",
        "ROS_DOMAIN_ID",
        "RMW_IMPLEMENTATION",
        "ROS_DISTRO",
        "CYCLONEDDS_URI",
        "COLCON_DEFAULTS_FILE",
    ]


def test_ros_env_pairs_opt_out(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(assets, "MAC_CYCLONEDDS_PATH", tmp_path / "cyclonedds.xml")
    cfg = Config.model_validate({"build": {"colcon_defaults": False}})
    keys = [p.split("=", 1)[0] for p in conda.ros_env_pairs(cfg)]
    assert "COLCON_DEFAULTS_FILE" not in keys
    assert "CYCLONEDDS_URI" in keys  # 나머지 주입은 유지

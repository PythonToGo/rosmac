from pathlib import Path

import pytest

from rosmac import sim


def test_load_packaged_preset() -> None:
    p = sim.load_preset("panda-moveit")
    assert p.name == "panda-moveit"
    assert "ros-humble-moveit" in p.vm_apt
    assert p.launch.cmd.startswith("ros2 launch")
    assert p.health_topics[0].name == "/joint_states"


def test_unknown_preset_lists_available() -> None:
    with pytest.raises(KeyError) as exc:
        sim.load_preset("no-such-preset")
    assert "panda-moveit" in exc.value.args[0]


def test_user_preset_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sim, "USER_PRESET_DIR", tmp_path)
    (tmp_path / "panda-moveit.yaml").write_text("name: panda-moveit\nlaunch: {cmd: echo custom}\n")
    p = sim.load_preset("panda-moveit")
    assert p.launch.cmd == "echo custom"


def test_nav2_preset_declares_bridge_scope() -> None:
    p = sim.load_preset("nav2-diffbot")
    assert p.name == "nav2-diffbot"
    assert "ros-humble-navigation2" in p.vm_apt
    assert p.bridge_allow is not None
    assert p.bridge_allow["action_servers"] == ["/navigate_to_pose"]
    assert "/scan" in p.bridge_allow["publishers"]
    assert "/cmd_vel" in p.bridge_allow["subscribers"]
    assert p.health_topics[0].name == "/scan"


def test_preset_without_bridge_allow_is_unscoped() -> None:
    # 기존 소형 프리셋은 무스코프(bridge_allow None) — 기존 동작 유지 (임계 미만)
    assert sim.load_preset("panda-moveit").bridge_allow is None
    assert sim.load_preset("gazebo-diffbot").bridge_allow is None


def test_bridge_scope_config_fills_all_six_categories() -> None:
    # 미지정 카테고리도 빈 목록으로 명시 — "전부 허용" 기본값으로 새지 않게 (KI-30)
    import json

    cfg = json.loads(sim.bridge_scope_config({"action_servers": ["/navigate_to_pose"]}))
    allow = cfg["plugins"]["ros2dds"]["allow"]
    assert set(allow.keys()) == {
        "publishers",
        "subscribers",
        "service_servers",
        "service_clients",
        "action_servers",
        "action_clients",
    }
    assert allow["action_servers"] == ["/navigate_to_pose"]
    assert allow["service_servers"] == []  # 내부 서비스 deny (포화 방지)


def test_bridge_scope_always_allows_doctor_roundtrip() -> None:
    # doctor C8 왕복 토픽은 스코프 중에도 자가진단되도록 pub/sub에 상시 주입
    import json

    allow = json.loads(sim.bridge_scope_config({"publishers": ["/scan"]}))[
        "plugins"
    ]["ros2dds"]["allow"]
    assert "/rosmac/doctor/.*" in allow["publishers"]
    assert "/rosmac/doctor/.*" in allow["subscribers"]
    assert "/scan" in allow["publishers"]  # 프리셋 지정 항목도 보존

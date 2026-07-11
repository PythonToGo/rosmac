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


def test_nav2_preset_loads_unscoped() -> None:
    # nav2-diffbot은 무스코프 — 브리지 리셋(KI-17/KI-30 정정, sim 시작 시)이 진짜 해법
    p = sim.load_preset("nav2-diffbot")
    assert p.name == "nav2-diffbot"
    assert "ros-humble-navigation2" in p.vm_apt
    assert not hasattr(p, "bridge_allow")  # 스코핑 메커니즘 제거됨
    assert p.health_topics[0].name == "/scan"

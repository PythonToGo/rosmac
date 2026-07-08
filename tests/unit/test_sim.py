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

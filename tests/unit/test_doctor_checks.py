"""doctor C12/C13/C14 판정 로직 (P5.3 ① — 2026-07-07 실사용 3대 장애의 감지기)."""

import pytest
from pathlib import Path

from rosmac import doctor
from rosmac.config import Config

CFG = Config()


# ── C12 데몬 응답성 ──────────────────────────────────────────────────────


def test_c12_no_daemon_is_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "_daemon_pids", lambda: [])
    r = doctor._C12DaemonResponsive().run(CFG)
    assert r.status == "PASS"


def test_c12_responsive_daemon_is_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "_daemon_pids", lambda: [111])
    monkeypatch.setattr(doctor.psview, "probe_daemon", lambda d: (True, 7))
    r = doctor._C12DaemonResponsive().run(CFG)
    assert r.status == "PASS" and "7ms" in r.detail


def test_c12_hung_daemon_is_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "_daemon_pids", lambda: [111])
    monkeypatch.setattr(doctor.psview, "probe_daemon", lambda d: (False, None))
    r = doctor._C12DaemonResponsive().run(CFG)
    assert r.status == "FAIL"
    assert "hung" in r.detail
    assert r.remedy is not None and "ros2 daemon stop" in r.remedy


# ── C13 필수 실행파일 ────────────────────────────────────────────────────


def test_c13_no_env_is_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.conda, "env_exists", lambda name: False)
    r = doctor._C13Executables().run(CFG)
    assert r.status == "WARN"


def test_c13_all_present_is_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.conda, "env_exists", lambda name: True)
    monkeypatch.setattr(doctor.conda, "run_in_env", lambda cfg, cmd, timeout: "")
    r = doctor._C13Executables().run(CFG)
    assert r.status == "PASS"


def test_c13_missing_xacro_is_fail_with_pkg_remedy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.conda, "env_exists", lambda name: True)
    monkeypatch.setattr(doctor.conda, "run_in_env", lambda cfg, cmd, timeout: "xacro\n")
    r = doctor._C13Executables().run(CFG)
    assert r.status == "FAIL"
    assert "xacro" in r.detail
    assert r.remedy is not None and "ros-humble-xacro" in r.remedy  # KI-26 매핑


# ── C14 그래프 오염 ──────────────────────────────────────────────────────


def _quiet_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "_daemon_pids", lambda: [111])
    monkeypatch.setattr(doctor.psview, "probe_daemon", lambda d: (True, 5))


def test_c14_sim_running_is_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    _quiet_daemon(monkeypatch)
    monkeypatch.setattr(doctor.sim, "session_alive", lambda cfg: True)
    r = doctor._C14GraphPollution().run(CFG)
    assert r.status == "PASS"


def test_c14_clean_graph_is_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    _quiet_daemon(monkeypatch)
    monkeypatch.setattr(doctor.sim, "session_alive", lambda cfg: False)
    monkeypatch.setattr(doctor.psview, "run_ros", lambda cfg, args: None)
    r = doctor._C14GraphPollution().run(CFG)
    assert r.status == "PASS"


def test_c14_unexpected_publisher_is_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    _quiet_daemon(monkeypatch)
    monkeypatch.setattr(doctor.sim, "session_alive", lambda cfg: False)
    monkeypatch.setattr(
        doctor.psview,
        "run_ros",
        lambda cfg, args: "Node name: stray_state_publisher\nSubscription count: 0",
    )
    r = doctor._C14GraphPollution().run(CFG)
    assert r.status == "WARN"
    assert "stray_state_publisher" in r.detail


def test_c14_hung_daemon_is_warn_not_hang(monkeypatch: pytest.MonkeyPatch) -> None:
    """데몬 hang 시 그래프 질의로 같이 매달리지 않고 WARN으로 비켜간다."""
    monkeypatch.setattr(doctor, "_daemon_pids", lambda: [111])
    monkeypatch.setattr(doctor.psview, "probe_daemon", lambda d: (False, None))
    r = doctor._C14GraphPollution().run(CFG)
    assert r.status == "WARN" and "C12" in r.detail


# ── C16 로봇 링크 (E.15-R4) ──────────────────────────────────────────────

ROBOT_CFG = Config.model_validate({"robot": {"host": "192.168.0.42"}})
_EP = "tcp/192.168.0.42:7447"
_LOG_2 = (
    "New ROS 2 bridge detected: aaaa\n"
    "New ROS 2 bridge detected: bbbb\n"
    "New ROS 2 bridge detected: aaaa\n"  # 재감지 중복은 세지 않음
)


def test_count_bridge_sessions_dedups() -> None:
    assert doctor.count_bridge_sessions(_LOG_2) == 2
    assert doctor.count_bridge_sessions("") == 0


def test_c16_not_configured_is_skip() -> None:
    r = doctor._C16RobotLink().run(CFG)
    assert r.status == "SKIP"


def test_c16_unreachable_is_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.bridge, "robot_reachable", lambda cfg, timeout=3.0: False)
    r = doctor._C16RobotLink().run(ROBOT_CFG)
    assert r.status == "FAIL"
    assert r.remedy is not None and "robot-setup.md" in r.remedy


def test_c16_drift_is_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.bridge, "robot_reachable", lambda cfg, timeout=3.0: True)
    monkeypatch.setattr(doctor.bridge, "running_cmdline", lambda: "bridge -e tcp/127.0.0.1:7447")
    r = doctor._C16RobotLink().run(ROBOT_CFG)
    assert r.status == "WARN" and "drift" in r.detail
    assert r.remedy is not None and "down --keep-vm" in r.remedy


def test_c16_session_missing_is_warn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(doctor.bridge, "robot_reachable", lambda cfg, timeout=3.0: True)
    monkeypatch.setattr(doctor.bridge, "running_cmdline", lambda: f"bridge -e {_EP}")
    log = tmp_path / "bridge.log"
    log.write_text("New ROS 2 bridge detected: aaaa\n")  # VM 세션뿐
    monkeypatch.setattr(doctor.bridge, "LOG_PATH", log)
    monkeypatch.setattr(doctor.lima, "state", lambda name: doctor.lima.VmState.RUNNING)
    r = doctor._C16RobotLink().run(ROBOT_CFG)
    assert r.status == "WARN" and "handshake" in r.detail


def test_c16_established_is_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(doctor.bridge, "robot_reachable", lambda cfg, timeout=3.0: True)
    monkeypatch.setattr(doctor.bridge, "running_cmdline", lambda: f"bridge -e {_EP}")
    log = tmp_path / "bridge.log"
    log.write_text(_LOG_2)
    monkeypatch.setattr(doctor.bridge, "LOG_PATH", log)
    monkeypatch.setattr(doctor.lima, "state", lambda name: doctor.lima.VmState.RUNNING)
    r = doctor._C16RobotLink().run(ROBOT_CFG)
    assert r.status == "PASS"

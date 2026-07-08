"""doctor --fix 픽서 3종 (P5.3 ②) — 자가 진단·안전 조건·보고."""

from pathlib import Path

import pytest
import yaml

from rosmac import doctor
from rosmac.config import Config

CFG = Config()


# ── fix: hung daemon ─────────────────────────────────────────────────────


def test_fix_daemon_noop_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "_daemon_pids", lambda: [])
    r = doctor._fix_hung_daemon(CFG)
    assert not r.applied


def test_fix_daemon_noop_when_responsive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "_daemon_pids", lambda: [42])
    monkeypatch.setattr(doctor.psview, "probe_daemon", lambda d: (True, 3))
    r = doctor._fix_hung_daemon(CFG)
    assert not r.applied


def test_fix_daemon_kills_and_restarts(monkeypatch: pytest.MonkeyPatch) -> None:
    killed: list[tuple[int, int]] = []
    probes = iter([(False, None), (True, 4)])  # 수리 전 hang → 수리 후 응답
    monkeypatch.setattr(doctor, "_daemon_pids", lambda: [42])
    monkeypatch.setattr(doctor.psview, "probe_daemon", lambda d: next(probes))
    monkeypatch.setattr(doctor.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(doctor.conda, "run_in_env", lambda cfg, cmd, timeout: "")
    r = doctor._fix_hung_daemon(CFG)
    assert r.applied
    assert (42, doctor.signal.SIGKILL) in killed
    assert "restarted (4ms)" in r.detail


# ── fix: orphan bridge sweep ─────────────────────────────────────────────


def test_fix_orphans_noop_when_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(doctor, "_list_ros_procs", lambda: [])
    monkeypatch.setattr(doctor.bridge, "PID_PATH", tmp_path / "pid")
    r = doctor._fix_orphan_bridges(CFG)
    assert not r.applied


def test_fix_orphans_terminates_only_orphans(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    procs = [
        doctor.psview.ProcInfo(pid=100, command="zenoh-bridge-ros2dds -e tcp/127.0.0.1:7447"),
        doctor.psview.ProcInfo(pid=200, command="zenoh-bridge-ros2dds -e tcp/127.0.0.1:7448"),
    ]
    pidfile = tmp_path / "pid"
    pidfile.write_text("100")  # 100 = 정규 브리지, 200 = 고아
    dead: set[int] = set()
    signals: list[tuple[int, int]] = []

    def fake_kill(pid: int, sig: int) -> None:
        if sig == 0:
            if pid in dead:
                raise OSError("dead")
            return
        signals.append((pid, sig))
        if sig == doctor.signal.SIGTERM:
            dead.add(pid)  # SIGTERM에 즉시 종료하는 정상 시나리오

    monkeypatch.setattr(doctor, "_list_ros_procs", lambda: procs)
    monkeypatch.setattr(doctor.bridge, "PID_PATH", pidfile)
    monkeypatch.setattr(doctor.os, "kill", fake_kill)
    r = doctor._fix_orphan_bridges(CFG)
    assert r.applied
    assert signals == [(200, doctor.signal.SIGTERM)]  # 정규 브리지(100)는 불가침
    assert "SIGKILL" not in r.detail


# ── fix: lima UDP rules (KI-24/KI-27) ────────────────────────────────────


def _yaml_without_rules(tmp_path: Path) -> Path:
    p = tmp_path / "lima.yaml"
    p.write_text(
        yaml.safe_dump(
            {"portForwards": [{"guestPort": 7447, "hostPort": 7447}], "cpus": 4},
            sort_keys=False,
        )
    )
    return p


def test_ensure_udp_rules_inserts_both_on_top(tmp_path: Path) -> None:
    p = _yaml_without_rules(tmp_path)
    assert doctor.ensure_udp_ignore_rules(p) == 2
    pf = yaml.safe_load(p.read_text())["portForwards"]
    assert pf[0]["proto"] == "udp" and pf[0]["ignore"] is True
    assert pf[1]["guestIP"] == "0.0.0.0"
    assert pf[2] == {"guestPort": 7447, "hostPort": 7447}  # 기존 규칙은 뒤로 보존


def test_ensure_udp_rules_idempotent(tmp_path: Path) -> None:
    p = _yaml_without_rules(tmp_path)
    doctor.ensure_udp_ignore_rules(p)
    before = p.read_text()
    assert doctor.ensure_udp_ignore_rules(p) == 0  # 재실행 무변경
    assert p.read_text() == before


def test_ensure_udp_rules_partial_insert(tmp_path: Path) -> None:
    p = tmp_path / "lima.yaml"
    p.write_text(yaml.safe_dump({"portForwards": [dict(doctor._UDP_IGNORE_PLAIN)]}))
    assert doctor.ensure_udp_ignore_rules(p) == 1  # 0.0.0.0 규칙만 보충


def test_fix_lima_rules_noop_when_vm_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(doctor.Path, "home", classmethod(lambda cls: tmp_path))
    r = doctor._fix_lima_udp_rules(CFG)
    assert not r.applied and "not found" in r.detail

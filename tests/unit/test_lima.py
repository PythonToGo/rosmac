import subprocess

import pytest

from rosmac import lima


def _cp(stdout: str = "", returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_state_running(monkeypatch: pytest.MonkeyPatch) -> None:
    out = '{"name":"rosmac","status":"Running","arch":"aarch64"}\n'
    monkeypatch.setattr(lima, "_run", lambda cmd, timeout=60: _cp(stdout=out))
    assert lima.state("rosmac") is lima.VmState.RUNNING


def test_state_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lima, "_run", lambda cmd, timeout=60: _cp(stdout=""))
    assert lima.state("rosmac") is lima.VmState.ABSENT


def test_state_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    out = '{"name":"rosmac","status":"Stopped"}\n{"name":"other","status":"Running"}\n'
    monkeypatch.setattr(lima, "_run", lambda cmd, timeout=60: _cp(stdout=out))
    assert lima.state("rosmac") is lima.VmState.STOPPED


def test_failure_raises_with_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        lima, "_run", lambda cmd, timeout=60: _cp(returncode=1, stderr="boom: no such instance")
    )
    with pytest.raises(RuntimeError, match="boom: no such instance"):
        lima.stop("rosmac")

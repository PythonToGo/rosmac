"""limactl 서브프로세스 래퍼. 모든 외부 호출은 _run 하나를 거친다 (테스트 mock 지점)."""

import json
import subprocess
from enum import Enum


class VmState(Enum):
    ABSENT = "absent"
    STOPPED = "Stopped"
    RUNNING = "Running"


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _check(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    p = _run(cmd, timeout)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed (exit {p.returncode}): {p.stderr.strip()}")
    return p


def state(name: str) -> VmState:
    p = _check(["limactl", "list", "--json"])
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        info = json.loads(line)
        if info.get("name") == name:
            status = info.get("status", "")
            return VmState.RUNNING if status == "Running" else VmState.STOPPED
    return VmState.ABSENT


def start(name: str, template_path: str | None = None, timeout: int = 1800) -> None:
    """VM 기동. template_path가 있으면 신규 생성(프로비저닝 포함).

    주의: limactl start는 provision 실패에도 exit 0을 반환한다 (Phase 0 실측) —
    설치 완료 검증은 호출자(init)가 후검증한다.
    """
    cmd = ["limactl", "start", f"--name={name}", "--tty=false"]
    if template_path:
        cmd.append(template_path)
    _check(cmd, timeout=timeout)


def stop(name: str, timeout: int = 120) -> None:
    _check(["limactl", "stop", name], timeout=timeout)


def delete(name: str, timeout: int = 120) -> None:
    _check(["limactl", "delete", "-f", name], timeout=timeout)


def shell(name: str, cmd: str, timeout: int = 60) -> str:
    """VM 안에서 명령 실행, stdout 반환. 로그인 셸(bash -lc) 경유 (부록 C-1 예외)."""
    p = _check(["limactl", "shell", name, "--", "bash", "-lc", cmd], timeout=timeout)
    return p.stdout

"""limactl 서브프로세스 래퍼. 모든 외부 호출은 _run 하나를 거친다 (테스트 mock 지점)."""

import json
import subprocess
from enum import Enum

from rosmac.errors import RosmacError


class VmState(Enum):
    ABSENT = "absent"
    STOPPED = "Stopped"
    RUNNING = "Running"


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _check(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    p = _run(cmd, timeout)
    if p.returncode != 0:
        raise RosmacError(f"{' '.join(cmd)} failed (exit {p.returncode}): {p.stderr.strip()}")
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


def push(name: str, content: str, dest: str, timeout: int = 60) -> None:
    """텍스트 파일을 VM의 dest 경로로 쓴다 (디렉토리 자동 생성)."""
    p = subprocess.run(
        [
            "limactl",
            "shell",
            name,
            "--",
            "bash",
            "-c",
            f'mkdir -p "$(dirname {dest})" && cat > {dest}',
        ],
        input=content,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if p.returncode != 0:
        raise RosmacError(f"push to {dest} failed (exit {p.returncode}): {p.stderr.strip()}")


def shell(name: str, cmd: str, timeout: int = 60) -> str:
    """VM 안에서 명령 실행, stdout 반환. 로그인 셸(bash -lc) 경유 (부록 C-1 예외)."""
    p = _check(["limactl", "shell", name, "--", "bash", "-lc", cmd], timeout=timeout)
    return p.stdout


def push_tree(name: str, src_dir: str, dest: str, timeout: int = 600) -> None:
    """디렉토리 트리를 tar 파이프로 VM에 복사 — dest 내용을 통째로 교체 (P4.4, D14).

    limactl copy -r은 버전별 동작 편차가 있어 tar 파이프를 쓴다.
    dest는 호출자가 ~/rosmac-ws/<이름>/src 고정 프리픽스로만 만든다 (rm -rf 안전장치).
    """
    import shlex

    if not dest.startswith("~/rosmac-ws/"):
        raise ValueError(f"push_tree dest must be under ~/rosmac-ws/: {dest}")
    inner = f"rm -rf {shlex.quote(dest)} && mkdir -p {shlex.quote(dest)} && tar -C {shlex.quote(dest)} -xf -"
    # shlex.quote가 ~를 감싸면 확장이 안 되므로 dest의 ~는 $HOME으로 치환
    inner = inner.replace("'~/", '"$HOME"\'/')
    tar = subprocess.Popen(["tar", "-C", src_dir, "-cf", "-", "."], stdout=subprocess.PIPE)
    try:
        p = subprocess.run(
            ["limactl", "shell", name, "--", "bash", "-c", inner],
            stdin=tar.stdout,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    finally:
        if tar.stdout:
            tar.stdout.close()
        tar_rc = tar.wait()
    if tar_rc != 0:
        raise RosmacError(f"tar creation failed (exit {tar_rc}) — source: {src_dir}")
    if p.returncode != 0:
        raise RosmacError(f"VM transfer failed (exit {p.returncode}): {p.stderr.strip()}")

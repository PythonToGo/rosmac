"""맥 쪽 zenoh 브리지: 바이너리 확보(버전 핀+sha256) + 프로세스 관리(pidfile).

- 이중 실행 금지 (R6): is_running()이면 start는 no-op
- 종료는 SIGTERM → 3초 → SIGKILL (KI-17: SIGKILL만 쓰면 상대 브리지에 라우트 잔재)
"""

import hashlib
import os
import signal
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path

from rosmac.config import Config
from rosmac.errors import RosmacError

ROSMAC_HOME = Path.home() / ".rosmac"
BIN_PATH = ROSMAC_HOME / "bin" / "zenoh-bridge-ros2dds"
PID_PATH = ROSMAC_HOME / "run" / "bridge.pid"
LOG_PATH = ROSMAC_HOME / "log" / "bridge.log"


def _download_url(version: str) -> str:
    return (
        "https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds/releases/download/"
        f"{version}/zenoh-plugin-ros2dds-{version}-aarch64-apple-darwin-standalone.zip"
    )


def ensure_binary(cfg: Config) -> bool:
    """바이너리가 없으면 다운로드+검증+설치. 설치했으면 True, 이미 있었으면 False."""
    if BIN_PATH.exists():
        return False
    BIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    zip_path = BIN_PATH.parent / "bridge-darwin.zip"
    urllib.request.urlretrieve(_download_url(cfg.bridge.version), zip_path)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if digest != cfg.bridge.sha256_darwin:
        zip_path.unlink()
        raise RosmacError(
            f"zenoh-bridge download sha256 mismatch: expected {cfg.bridge.sha256_darwin}, got {digest}"
        )
    with zipfile.ZipFile(zip_path) as z:
        z.extract("zenoh-bridge-ros2dds", BIN_PATH.parent)
    zip_path.unlink()
    BIN_PATH.chmod(0o755)
    return True


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    # PID 재사용 방어: cmdline에 zenoh-bridge가 맞는지 확인
    p = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True)
    return "zenoh-bridge-ros2dds" in p.stdout


def is_running() -> bool:
    if not PID_PATH.exists():
        return False
    try:
        pid = int(PID_PATH.read_text().strip())
    except ValueError:
        PID_PATH.unlink()
        return False
    if _pid_alive(pid):
        return True
    PID_PATH.unlink()  # 죽은 pidfile 정리
    return False


def start(cfg: Config) -> bool:
    """브리지 기동. 이미 실행 중이면 no-op(False), 새로 띄웠으면 True."""
    if is_running():
        return False
    if not BIN_PATH.exists():
        raise RosmacError(f"{BIN_PATH} not found — run `rosmac init` first")
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOG_PATH.exists():  # 로그 rotate
        LOG_PATH.replace(LOG_PATH.with_suffix(".log.1"))
    from rosmac.assets import ensure_mac_cyclonedds

    env = dict(os.environ)
    env.update(
        ROS_LOCALHOST_ONLY="1",
        ROS_DOMAIN_ID=str(cfg.ros.domain_id),
        ROS_DISTRO=cfg.ros.distro,  # 없으면 브리지가 'iron' 가정 (Phase 0 실측)
        CYCLONEDDS_URI=ensure_mac_cyclonedds(),  # KI-23
    )
    with LOG_PATH.open("w") as log:
        proc = subprocess.Popen(
            [str(BIN_PATH), "-e", f"tcp/127.0.0.1:{cfg.bridge.port}"],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,  # rosmac 종료와 무관하게 생존
        )
    # 스폰 직후 사망 감지 (KI-20: 고아 브리지가 [::]:{port}를 점유하면 즉사)
    time.sleep(1.5)
    if proc.poll() is not None:
        tail = LOG_PATH.read_text()[-500:] if LOG_PATH.exists() else ""
        raise RosmacError(
            f"mac bridge died right after start (exit {proc.returncode}). "
            f"Check for orphan bridges: pgrep -f zenoh-bridge-ros2dds\nLog tail:\n{tail}"
        )
    PID_PATH.write_text(str(proc.pid))
    return True


def _terminate(pid: int, grace_seconds: float) -> None:
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)


def _orphan_pids() -> list[int]:
    """pidfile 밖에서 돌고 있는 rosmac 브리지 프로세스 (R6: 좀비 정리 대상)."""
    p = subprocess.run(["pgrep", "-f", str(BIN_PATH)], capture_output=True, text=True)
    return [int(line) for line in p.stdout.split() if line.strip()]


def stop(grace_seconds: float = 3.0) -> bool:
    """SIGTERM → 대기 → SIGKILL. pidfile 밖 고아 브리지도 함께 정리 (KI-20)."""
    stopped = False
    if is_running():
        _terminate(int(PID_PATH.read_text().strip()), grace_seconds)
        stopped = True
    PID_PATH.unlink(missing_ok=True)
    for pid in _orphan_pids():
        _terminate(pid, grace_seconds)
        stopped = True
    return stopped

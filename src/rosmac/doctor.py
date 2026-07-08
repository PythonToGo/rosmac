"""rosmac doctor — C1~C14 진단. 새 체크는 CHECKS에 추가만 하면 된다."""

import os
import shutil
import socket
import subprocess
import uuid
from typing import Literal, NamedTuple, Protocol

from rosmac import bridge, conda, lima, psview, sim
from rosmac.config import Config


class CheckResult(NamedTuple):
    name: str
    status: Literal["PASS", "WARN", "FAIL"]
    detail: str
    remedy: str | None = None  # FAIL일 때 사용자에게 보여줄 한 줄 처방


class Check(Protocol):
    name: str

    def run(self, cfg: Config) -> CheckResult: ...


class _C1Lima:
    name = "C1 lima install/version"

    def run(self, cfg: Config) -> CheckResult:
        if not shutil.which("limactl"):
            return CheckResult(self.name, "FAIL", "limactl not found", "brew install lima")
        p = subprocess.run(["limactl", "--version"], capture_output=True, text=True)
        return CheckResult(self.name, "PASS", p.stdout.strip())


class _C2Vm:
    name = "C2 VM existence/state"

    def run(self, cfg: Config) -> CheckResult:
        st = lima.state(cfg.vm.name)
        if st is lima.VmState.RUNNING:
            return CheckResult(self.name, "PASS", "Running")
        if st is lima.VmState.STOPPED:
            return CheckResult(self.name, "WARN", "Stopped", "rosmac up")
        return CheckResult(self.name, "FAIL", "VM not found", "rosmac init")


class _C3CondaEnv:
    name = "C3 conda env"

    def run(self, cfg: Config) -> CheckResult:
        if conda.env_exists(cfg.conda_env):
            return CheckResult(self.name, "PASS", f"'{cfg.conda_env}' present")
        return CheckResult(self.name, "FAIL", f"'{cfg.conda_env}' missing", "rosmac init")


class _C4EnvVars:
    name = "C4 required env vars"

    def run(self, cfg: Config) -> CheckResult:
        expected = {
            "ROS_LOCALHOST_ONLY": "1",
            "ROS_DOMAIN_ID": str(cfg.ros.domain_id),
            "RMW_IMPLEMENTATION": cfg.ros.rmw,
        }
        wrong = [k for k, v in expected.items() if os.environ.get(k) != v]
        if not wrong:
            return CheckResult(self.name, "PASS", "all set in current shell")
        return CheckResult(
            self.name,
            "WARN",
            f"unset/mismatched in current shell: {', '.join(wrong)}",
            "enter `rosmac shell` when using ros2 directly (KI-6 prevention)",
        )


class _C5Port:
    name = "C5 port reachability"

    def run(self, cfg: Config) -> CheckResult:
        # 주의: 맥 브리지도 [::]:{port}를 listen하므로 (router 모드) VM이 꺼져 있어도
        # TCP 연결이 성사될 수 있음 — VM 상태를 먼저 가려서 오탐 방지 (Phase 0 관찰)
        if lima.state(cfg.vm.name) is not lima.VmState.RUNNING:
            return CheckResult(
                self.name, "FAIL", "VM not running, so no port forwarding", "rosmac up"
            )
        try:
            with socket.create_connection(("127.0.0.1", cfg.bridge.port), timeout=2):
                return CheckResult(self.name, "PASS", f"127.0.0.1:{cfg.bridge.port} open")
        except OSError as e:
            return CheckResult(
                self.name, "FAIL", f"connection failed: {e}", "rosmac up (check VM/port forwarding)"
            )


class _C6MacBridge:
    name = "C6 mac bridge process"

    def run(self, cfg: Config) -> CheckResult:
        if bridge.is_running():
            return CheckResult(self.name, "PASS", f"pid {bridge.PID_PATH.read_text().strip()}")
        return CheckResult(self.name, "FAIL", "not running", "rosmac up")


class _C7VmBridge:
    name = "C7 VM bridge service"

    def run(self, cfg: Config) -> CheckResult:
        if lima.state(cfg.vm.name) is not lima.VmState.RUNNING:
            return CheckResult(self.name, "WARN", "VM not running — cannot determine", "rosmac up")
        out = lima.shell(cfg.vm.name, "systemctl is-active zenoh-bridge || true").strip()
        if out == "active":
            return CheckResult(self.name, "PASS", "systemd active")
        return CheckResult(
            self.name,
            "FAIL",
            f"state: {out}",
            f"limactl shell {cfg.vm.name} -- journalctl -u zenoh-bridge -n 50",
        )


class _C8RoundTrip:
    name = "C8 round-trip self test"

    def run(self, cfg: Config) -> CheckResult:
        import time

        topic = f"/rosmac/doctor/{uuid.uuid4().hex[:8]}"
        pub = None
        try:
            pub = subprocess.Popen(
                [
                    "limactl",
                    "shell",
                    cfg.vm.name,
                    "--",
                    "bash",
                    "-lc",
                    # bash -lc는 비인터랙티브 → .bashrc의 ROS 소싱에 도달 못 함 (KI-19)
                    f"source /opt/ros/{cfg.ros.distro}/setup.bash; "
                    f"export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID={cfg.ros.domain_id} "
                    f"RMW_IMPLEMENTATION={cfg.ros.rmw} "
                    f"CYCLONEDDS_URI=file:///etc/cyclonedds.xml; "
                    f"timeout 60 ros2 topic pub -r 5 {topic} std_msgs/msg/String 'data: ping'",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)  # 발행자·라우트 안정화 (브리지 경유 디스커버리 ~10s 관찰됨)
            out = conda.run_in_env(
                cfg, f"ros2 topic echo --once {topic} std_msgs/msg/String", timeout=40
            )
            if "ping" in out:
                return CheckResult(self.name, "PASS", f"{topic} round-trip received")
            return CheckResult(
                self.name,
                "FAIL",
                f"receive failed (output: {out[:80]!r})",
                f"check bridge log: {bridge.LOG_PATH}",
            )
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            return CheckResult(
                self.name, "FAIL", f"{e}"[:120], f"check bridge log: {bridge.LOG_PATH}"
            )
        finally:
            if pub is not None:
                pub.terminate()


# Phase 0.1 실측에서 깨진 dylib 없음 → 지문 DB는 비어 있음. R2 발생 시 여기에 추가.
BROKEN_DYLIB_FINGERPRINTS: list[str] = []


class _C9Dylib:
    name = "C9 RoboStack fingerprint"

    def run(self, cfg: Config) -> CheckResult:
        if not BROKEN_DYLIB_FINGERPRINTS:
            return CheckResult(self.name, "PASS", "fingerprint DB empty (Phase 0: 0 broken links)")
        return CheckResult(self.name, "WARN", "some fingerprint checks not implemented")


class _C10Sip:
    name = "C10 SIP status"

    def run(self, cfg: Config) -> CheckResult:
        p = subprocess.run(["csrutil", "status"], capture_output=True, text=True)
        enabled = "enabled" in p.stdout.lower()
        # 정보성: 우리는 SIP를 끄지 않는 것이 정상 전제 (절대 규칙 1)
        return CheckResult(
            self.name, "PASS" if enabled else "WARN", p.stdout.strip() or "cannot determine"
        )


class _C11Disk:
    name = "C11 disk space"

    def run(self, cfg: Config) -> CheckResult:
        usage = shutil.disk_usage(os.path.expanduser("~"))
        free_gb = usage.free / 1e9
        status: Literal["PASS", "WARN"] = "PASS" if free_gb > 20 else "WARN"
        return CheckResult(self.name, status, f"home volume free {free_gb:.0f}GB")


def _daemon_pids() -> list[int]:
    """맥의 ros2 데몬 pid 목록 (pgrep — 자기 cmdline엔 패턴이 없어 KI-18 자기매칭 없음)."""
    p = subprocess.run(["pgrep", "-f", "ros2cli.daemon"], capture_output=True, text=True)
    return [int(x) for x in p.stdout.split()]


class _C12DaemonResponsive:
    name = "C12 ros2 daemon responsiveness"

    def run(self, cfg: Config) -> CheckResult:
        pids = _daemon_pids()
        if not pids:
            return CheckResult(self.name, "PASS", "not started (auto-starts on first ros2 call)")
        responsive, latency = psview.probe_daemon(cfg.ros.domain_id)
        if responsive:
            return CheckResult(self.name, "PASS", f"pid {pids[0]} responsive ({latency}ms)")
        return CheckResult(
            self.name,
            "FAIL",
            f"pid {pids[0]} unresponsive (hung) — causes ros2 topic echo/list to wait forever"
            " (observed 2026-07-07)",
            "run `ros2 daemon stop && ros2 daemon start` in rosmac shell",
        )


# KI-26: xacro는 desktop 메타패키지에 없어 launch가 조용히 깨짐 — 존재를 상시 감시
_REQUIRED_EXECUTABLES = ("ros2", "colcon", "xacro")
_CONDA_PKG_OF = {"xacro": "ros-{distro}-xacro", "colcon": "colcon-common-extensions"}


class _C13Executables:
    name = "C13 required executables"

    def run(self, cfg: Config) -> CheckResult:
        if not conda.env_exists(cfg.conda_env):
            return CheckResult(
                self.name, "WARN", "conda env missing — cannot determine", "rosmac init"
            )
        probe = "; ".join(f"command -v {x} >/dev/null || echo {x}" for x in _REQUIRED_EXECUTABLES)
        try:
            missing = conda.run_in_env(cfg, probe, timeout=60).split()
        except RuntimeError as e:
            return CheckResult(self.name, "FAIL", f"{e}"[:120], "rosmac init")
        if not missing:
            return CheckResult(self.name, "PASS", ", ".join(_REQUIRED_EXECUTABLES) + " present")
        pkgs = " ".join(_CONDA_PKG_OF.get(m, m).format(distro=cfg.ros.distro) for m in missing)
        return CheckResult(
            self.name,
            "FAIL",
            f"missing from env: {', '.join(missing)}",
            f"micromamba install -n {cfg.conda_env} -c conda-forge -c {cfg.conda_channel} {pkgs}",
        )


class _C14GraphPollution:
    name = "C14 graph pollution"

    # 2026-07-07 실사용 장애: VM sim 잔존 스택의 /tf·/robot_description이 시각화 튕김 유발
    _WATCHED = ("/robot_description", "/tf")

    def run(self, cfg: Config) -> CheckResult:
        pids = _daemon_pids()
        if pids and not psview.probe_daemon(cfg.ros.domain_id)[0]:
            return CheckResult(self.name, "WARN", "daemon hung — cannot query graph (see C12)")
        if sim.session_alive(cfg):
            return CheckResult(self.name, "PASS", "sim session running — publishers are expected")
        polluted = []
        for topic in self._WATCHED:
            out = psview.run_ros(cfg, ["topic", "info", topic, "--verbose"])
            if out is None:
                continue  # 토픽 없음/질의 실패 — 오염 아님
            pubs = psview.parse_publisher_nodes(out)
            if pubs:
                polluted.append(f"{topic} ← {', '.join(pubs)}")
        if not polluted:
            return CheckResult(self.name, "PASS", "sim not running, no unexpected publishers")
        return CheckResult(
            self.name,
            "WARN",
            "publishers present while sim not running: " + "; ".join(polluted),
            "if not intentional, suspect leftover stack — check with rosmac ps (2026-07-07 flapping pattern)",
        )


CHECKS: list[Check] = [
    _C1Lima(),
    _C2Vm(),
    _C3CondaEnv(),
    _C4EnvVars(),
    _C5Port(),
    _C6MacBridge(),
    _C7VmBridge(),
    _C8RoundTrip(),
    _C9Dylib(),
    _C10Sip(),
    _C11Disk(),
    _C12DaemonResponsive(),
    _C13Executables(),
    _C14GraphPollution(),
]


def run_all(cfg: Config) -> list[CheckResult]:
    return [c.run(cfg) for c in CHECKS]

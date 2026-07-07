"""rosmac doctor — C1~C11 진단. 새 체크는 CHECKS에 추가만 하면 된다."""

import os
import shutil
import socket
import subprocess
import uuid
from typing import Literal, NamedTuple, Protocol

from rosmac import bridge, conda, lima
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
    name = "C1 lima 설치/버전"

    def run(self, cfg: Config) -> CheckResult:
        if not shutil.which("limactl"):
            return CheckResult(self.name, "FAIL", "limactl 없음", "brew install lima")
        p = subprocess.run(["limactl", "--version"], capture_output=True, text=True)
        return CheckResult(self.name, "PASS", p.stdout.strip())


class _C2Vm:
    name = "C2 VM 존재/상태"

    def run(self, cfg: Config) -> CheckResult:
        st = lima.state(cfg.vm.name)
        if st is lima.VmState.RUNNING:
            return CheckResult(self.name, "PASS", "Running")
        if st is lima.VmState.STOPPED:
            return CheckResult(self.name, "WARN", "Stopped", "rosmac up")
        return CheckResult(self.name, "FAIL", "VM 없음", "rosmac init")


class _C3CondaEnv:
    name = "C3 conda env"

    def run(self, cfg: Config) -> CheckResult:
        if conda.env_exists(cfg.conda_env):
            return CheckResult(self.name, "PASS", f"'{cfg.conda_env}' 존재")
        return CheckResult(self.name, "FAIL", f"'{cfg.conda_env}' 없음", "rosmac init")


class _C4EnvVars:
    name = "C4 필수 env vars"

    def run(self, cfg: Config) -> CheckResult:
        expected = {
            "ROS_LOCALHOST_ONLY": "1",
            "ROS_DOMAIN_ID": str(cfg.ros.domain_id),
            "RMW_IMPLEMENTATION": cfg.ros.rmw,
        }
        wrong = [k for k, v in expected.items() if os.environ.get(k) != v]
        if not wrong:
            return CheckResult(self.name, "PASS", "현재 셸에 전부 설정됨")
        return CheckResult(
            self.name,
            "WARN",
            f"현재 셸에 미설정/불일치: {', '.join(wrong)}",
            "ros2를 직접 쓸 땐 `rosmac shell`로 진입 (KI-6 예방)",
        )


class _C5Port:
    name = "C5 포트 도달성"

    def run(self, cfg: Config) -> CheckResult:
        try:
            with socket.create_connection(("127.0.0.1", cfg.bridge.port), timeout=2):
                return CheckResult(self.name, "PASS", f"127.0.0.1:{cfg.bridge.port} open")
        except OSError as e:
            return CheckResult(
                self.name, "FAIL", f"연결 실패: {e}", "rosmac up (VM/포트포워딩 점검)"
            )


class _C6MacBridge:
    name = "C6 맥 브리지 프로세스"

    def run(self, cfg: Config) -> CheckResult:
        if bridge.is_running():
            return CheckResult(self.name, "PASS", f"pid {bridge.PID_PATH.read_text().strip()}")
        return CheckResult(self.name, "FAIL", "실행 중 아님", "rosmac up")


class _C7VmBridge:
    name = "C7 VM 브리지 서비스"

    def run(self, cfg: Config) -> CheckResult:
        if lima.state(cfg.vm.name) is not lima.VmState.RUNNING:
            return CheckResult(self.name, "WARN", "VM이 실행 중이 아님 — 판단 불가", "rosmac up")
        out = lima.shell(cfg.vm.name, "systemctl is-active zenoh-bridge || true").strip()
        if out == "active":
            return CheckResult(self.name, "PASS", "systemd active")
        return CheckResult(
            self.name,
            "FAIL",
            f"상태: {out}",
            f"limactl shell {cfg.vm.name} -- journalctl -u zenoh-bridge -n 50",
        )


class _C8RoundTrip:
    name = "C8 왕복 자가 테스트"

    def run(self, cfg: Config) -> CheckResult:
        topic = f"/rosmac/doctor/{uuid.uuid4().hex[:8]}"
        pub = None
        try:
            pub = subprocess.Popen(
                [
                    "limactl", "shell", cfg.vm.name, "--", "bash", "-lc",
                    f"export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID={cfg.ros.domain_id} "
                    f"RMW_IMPLEMENTATION={cfg.ros.rmw}; "
                    f"timeout 20 ros2 topic pub -r 5 {topic} std_msgs/msg/String 'data: ping'",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            out = conda.run_in_env(
                cfg, f"ros2 topic echo --once {topic} std_msgs/msg/String", timeout=15
            )
            if "ping" in out:
                return CheckResult(self.name, "PASS", f"{topic} 왕복 수신")
            return CheckResult(
                self.name, "FAIL", f"수신 실패 (출력: {out[:80]!r})",
                f"브리지 로그 확인: {bridge.LOG_PATH}",
            )
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            return CheckResult(
                self.name, "FAIL", f"{e}"[:120], f"브리지 로그 확인: {bridge.LOG_PATH}"
            )
        finally:
            if pub is not None:
                pub.terminate()


# Phase 0.1 실측에서 깨진 dylib 없음 → 지문 DB는 비어 있음. R2 발생 시 여기에 추가.
BROKEN_DYLIB_FINGERPRINTS: list[str] = []


class _C9Dylib:
    name = "C9 RoboStack 지문"

    def run(self, cfg: Config) -> CheckResult:
        if not BROKEN_DYLIB_FINGERPRINTS:
            return CheckResult(self.name, "PASS", "지문 DB 비어 있음 (Phase 0: 깨진 링크 0건)")
        return CheckResult(self.name, "WARN", "지문 검사 미구현 항목 있음")


class _C10Sip:
    name = "C10 SIP 상태"

    def run(self, cfg: Config) -> CheckResult:
        p = subprocess.run(["csrutil", "status"], capture_output=True, text=True)
        enabled = "enabled" in p.stdout.lower()
        # 정보성: 우리는 SIP를 끄지 않는 것이 정상 전제 (절대 규칙 1)
        return CheckResult(
            self.name, "PASS" if enabled else "WARN", p.stdout.strip() or "확인 불가"
        )


class _C11Disk:
    name = "C11 디스크 여유"

    def run(self, cfg: Config) -> CheckResult:
        usage = shutil.disk_usage(os.path.expanduser("~"))
        free_gb = usage.free / 1e9
        status: Literal["PASS", "WARN"] = "PASS" if free_gb > 20 else "WARN"
        return CheckResult(self.name, status, f"홈 볼륨 여유 {free_gb:.0f}GB")


CHECKS: list[Check] = [
    _C1Lima(), _C2Vm(), _C3CondaEnv(), _C4EnvVars(), _C5Port(),
    _C6MacBridge(), _C7VmBridge(), _C8RoundTrip(), _C9Dylib(), _C10Sip(), _C11Disk(),
]


def run_all(cfg: Config) -> list[CheckResult]:
    return [c.run(cfg) for c in CHECKS]

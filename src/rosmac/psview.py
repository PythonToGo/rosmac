"""rosmac ps — 맥+VM의 ROS 프로세스·그래프 상태를 한 화면에 (P4.3).

2026-07-07 복합 장애(데몬 hang + VM sim 잔존 토픽 + 브리지 낡은 라우트 + 고아
프로세스)의 교훈으로 만든 관찰 도구. 설계 원칙:
- **모든 외부 호출에 타임아웃** — 관찰 도구 자체가 hang하면 존재 의미가 없다.
  특히 ros2 CLI는 데몬이 hang이면 무한 대기하므로, 데몬 응답성을 먼저 XMLRPC로
  프로브(5초 컷)하고 그 결과에 따라 그래프 질의를 분기한다.
- 실패는 죽지 않고 "질의 실패"로 표기하고 진행한다.

순수 판정 로직(파싱/경고)은 함수로 분리 — 유닛 테스트 대상.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import xmlrpc.client

from pydantic import BaseModel

from rosmac import bridge, conda, lima
from rosmac.config import Config
from rosmac.sim import SESSION as SIM_SESSION

# 이중 발행이 사고 신호인 핵심 토픽 (2026-07-07: VM sim 잔존 /tf가 시각화 튕김 유발)
CORE_TOPICS = ("/tf", "/tf_static", "/joint_states", "/robot_description", "/clock")

_SUBPROC_TIMEOUT = 15  # ros2 CLI 개별 호출 상한 (초)


class ProcInfo(BaseModel):
    pid: int
    command: str


class DaemonStatus(BaseModel):
    pid: int | None = None
    responsive: bool | None = None  # None = 프로세스 없음 (질의 안 함)
    latency_ms: int | None = None


class TopicPublishers(BaseModel):
    topic: str
    publishers: list[str]  # 노드 이름
    warning: str | None = None


class RobotLink(BaseModel):
    # D15 (E.15-R3): 로봇 유래 발행자는 zenoh 경유라 맥 그래프에서 구분 불가 —
    # 대신 링크 자체(설정·도달성·브리지 인자 반영 여부)를 관찰한다.
    endpoint: str  # tcp/<host>:<port>
    reachable: bool
    in_bridge_args: bool | None = None  # None = 맥 브리지가 안 떠 있어 판정 불가


class PsReport(BaseModel):
    daemon: DaemonStatus = DaemonStatus()
    bridge_pid: int | None = None  # pidfile과 일치하는 살아있는 브리지
    robot_link: RobotLink | None = None  # None = robot 미설정 (기존 사용자 무영향)
    orphan_bridges: list[ProcInfo] = []
    mac_nodes: list[ProcInfo] = []
    vm_state: str = "unknown"
    vm_units: dict[str, str] = {}  # zenoh-bridge / foxglove-bridge systemd 상태
    vm_sim_session: bool | None = None
    vm_ros_procs: list[ProcInfo] = []
    core_topics: list[TopicPublishers] = []
    graph_note: str | None = None  # 그래프 질의를 못 한 이유
    warnings: list[str] = []


# ── 순수 판정 로직 (유닛 테스트 대상) ──────────────────────────────────────


def parse_ps_lines(text: str, exclude_pids: set[int]) -> list[ProcInfo]:
    """`ps -axo pid=,command=` 출력에서 ROS 관련 프로세스만 추린다.

    KI-18 교훈: pgrep -f의 자기 매칭은 패턴 브래킷 트릭 대신
    **수집 후 자기/부모 PID 제외**로 푼다 (호출자가 exclude_pids 전달).
    """
    keep = re.compile(
        r"(--ros-args|zenoh-bridge-ros2dds|ros2-daemon|"
        r"\bros2 (launch|run|topic|service|action|bag|echo)\b)"
    )
    procs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid_s, cmd = line.split(None, 1)
            pid = int(pid_s)
        except ValueError:
            continue
        if pid in exclude_pids or not keep.search(cmd):
            continue
        procs.append(ProcInfo(pid=pid, command=cmd[:160]))
    return procs


def parse_publisher_nodes(topic_info_verbose: str) -> list[str]:
    """`ros2 topic info --verbose` 출력에서 **발행자** 노드 이름만 추출.

    출력은 Publisher 섹션들 다음에 'Subscription count:'가 온다 (humble 실측) —
    그 앞부분의 'Node name:' 줄만 취한다.
    """
    head = topic_info_verbose.split("Subscription count:")[0]
    return re.findall(r"Node name:\s*(\S+)", head)


# 브리지(bare DDS) 유래 발행자의 노드명 마커 (실측 2026-07-08):
# 맥 zenoh-bridge의 writer는 rcl 노드가 아니라 `_CREATED_BY_BARE_DDS_APP_`로 보이고,
# VM 브리지가 노드로 잡히면 `zenoh_bridge_ros2dds`로 보인다.
_BRIDGE_MARKERS = ("zenoh_bridge", "_CREATED_BY_BARE_DDS_APP_")


def core_topic_warning(publishers: list[str]) -> str | None:
    """핵심 토픽의 발행자 구성에서 사고 패턴을 판정한다."""
    if len(publishers) >= 2:
        via_bridge = [p for p in publishers if any(m in p for m in _BRIDGE_MARKERS)]
        local = [p for p in publishers if not any(m in p for m in _BRIDGE_MARKERS)]
        if via_bridge and local:
            return (
                f"{len(publishers)} publishers — local ({', '.join(local)}) and "
                f"bridge-origin (VM) publishing simultaneously. Check for leftover VM stack "
                f"in `rosmac sim status` / the VM section of `rosmac ps` (2026-07-07 flapping pattern)"
            )
        return (
            f"{len(publishers)} publishers ({', '.join(publishers)}) — verify this is intentional"
        )
    return None


def find_orphan_bridges(procs: list[ProcInfo], pidfile_pid: int | None) -> list[ProcInfo]:
    """pidfile과 무관하게 살아있는 zenoh-bridge 프로세스 = 고아 (KI-20 패턴)."""
    return [p for p in procs if "zenoh-bridge-ros2dds" in p.command and p.pid != pidfile_pid]


def robot_link_status(endpoint: str, bridge_cmdline: str | None, reachable: bool) -> RobotLink:
    """로봇 링크 판정. 브리지가 robot 설정 전에 떴으면 in_bridge_args=False (드리프트)."""
    in_args = None if bridge_cmdline is None else endpoint in bridge_cmdline
    return RobotLink(endpoint=endpoint, reachable=reachable, in_bridge_args=in_args)


# ── 수집 (외부 호출 — 전부 타임아웃) ──────────────────────────────────────


def probe_daemon(domain_id: int, timeout_s: float = 5.0) -> tuple[bool, int | None]:
    """ros2 데몬 XMLRPC 응답성 (2026-07-07 실측 검증 방법). (응답 여부, ms)."""
    import time

    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout_s)
    try:
        proxy = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{11511 + domain_id}/ros2cli/")
        t0 = time.monotonic()
        proxy.system.listMethods()
        return True, int((time.monotonic() - t0) * 1000)
    except Exception:
        return False, None
    finally:
        socket.setdefaulttimeout(old)


def run_ros(cfg: Config, args: list[str], timeout: int = _SUBPROC_TIMEOUT) -> str | None:
    """ros2 CLI를 rosmac env로 실행. 실패/타임아웃이면 None (절대 raise 안 함)."""
    cmd = [
        "micromamba",
        "run",
        "-n",
        cfg.conda_env,
        "env",
        *conda.ros_env_pairs(cfg),
        "ros2",
        *args,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=conda._env())
    except subprocess.TimeoutExpired:
        return None
    return p.stdout if p.returncode == 0 else None


def collect(cfg: Config) -> PsReport:
    r = PsReport()

    # 1) 맥 프로세스 (자기 자신·부모 제외 — KI-18)
    try:
        ps_out = subprocess.run(
            ["ps", "-axo", "pid=,command="], capture_output=True, text=True, timeout=10
        ).stdout
    except subprocess.TimeoutExpired:
        ps_out = ""
    procs = parse_ps_lines(ps_out, exclude_pids={os.getpid(), os.getppid()})

    pidfile_pid: int | None = None
    if bridge.PID_PATH.exists():
        try:
            candidate = int(bridge.PID_PATH.read_text().strip())
            if any(p.pid == candidate for p in procs):
                pidfile_pid = candidate
        except ValueError:
            pass
    r.bridge_pid = pidfile_pid
    r.orphan_bridges = find_orphan_bridges(procs, pidfile_pid)
    if r.orphan_bridges:
        r.warnings.append(
            f"{len(r.orphan_bridges)} orphan zenoh-bridge(s) (KI-20) — "
            f"clean up with `rosmac down --keep-vm && rosmac up`"
        )

    # 로봇 링크 (D15) — 설정된 경우에만; 로봇 유래 발행자는 그래프에서 구분 불가하므로
    # 링크 상태(도달성 + 브리지 인자 드리프트)를 대신 관찰한다.
    if cfg.robot.host:
        cmdline = next((p.command for p in procs if p.pid == pidfile_pid), None)
        r.robot_link = robot_link_status(
            bridge.robot_endpoint(cfg), cmdline, bridge.robot_reachable(cfg)
        )
        if r.robot_link.in_bridge_args is False:
            r.warnings.append(
                f"running bridge has no robot endpoint {r.robot_link.endpoint} — "
                "restart with `rosmac down --keep-vm && rosmac up`"
            )

    daemon_procs = [p for p in procs if "ros2-daemon" in p.command]
    r.mac_nodes = [
        p for p in procs if p not in daemon_procs and "zenoh-bridge-ros2dds" not in p.command
    ]

    # 2) 데몬 응답성
    if daemon_procs:
        responsive, latency = probe_daemon(cfg.ros.domain_id)
        r.daemon = DaemonStatus(pid=daemon_procs[0].pid, responsive=responsive, latency_ms=latency)
        if not responsive:
            r.warnings.append(
                "ros2 daemon unresponsive (hung) — why `ros2 topic echo/list` waits forever. "
                "Fix: run `ros2 daemon stop && ros2 daemon start` inside rosmac shell"
            )

    # 3) VM
    try:
        vm_state = lima.state(cfg.vm.name)
        r.vm_state = vm_state.value
    except (RuntimeError, subprocess.TimeoutExpired):
        r.vm_state = "query failed"
        vm_state = None
    if vm_state == lima.VmState.RUNNING:
        combined = (
            "echo UNIT_Z=$(systemctl is-active zenoh-bridge 2>/dev/null); "
            "echo UNIT_F=$(systemctl is-active foxglove-bridge 2>/dev/null); "
            f"tmux has-session -t {SIM_SESSION} 2>/dev/null && echo SIM=yes || echo SIM=no; "
            "ps -eo pid=,args="
        )
        try:
            out = lima.shell(cfg.vm.name, combined, timeout=30)
        except (RuntimeError, subprocess.TimeoutExpired):
            out = ""
        for line in out.splitlines():
            if line.startswith("UNIT_Z="):
                r.vm_units["zenoh-bridge"] = line.removeprefix("UNIT_Z=") or "unknown"
            elif line.startswith("UNIT_F="):
                r.vm_units["foxglove-bridge"] = line.removeprefix("UNIT_F=") or "unknown"
            elif line.startswith("SIM="):
                r.vm_sim_session = line.endswith("yes")
        vm_ps = "\n".join(ln for ln in out.splitlines() if not ln.startswith(("UNIT_", "SIM=")))
        r.vm_ros_procs = [
            p for p in parse_ps_lines(vm_ps, exclude_pids=set()) if "ros2-daemon" not in p.command
        ]

    # 4) 그래프 — 데몬이 살아있을 때만 발행자 질의 (topic info는 데몬 의존)
    if r.daemon.responsive:
        for topic in CORE_TOPICS:
            info = run_ros(cfg, ["topic", "info", topic, "--verbose"])
            if info is None:
                continue  # 존재하지 않는 토픽 등 — 표시 생략
            pubs = parse_publisher_nodes(info)
            warn = core_topic_warning(pubs)
            r.core_topics.append(TopicPublishers(topic=topic, publishers=pubs, warning=warn))
            if warn:
                r.warnings.append(f"{topic}: {warn}")
    else:
        r.graph_note = (
            "daemon unresponsive — publisher query skipped"
            if r.daemon.pid
            else "ros2 daemon not running — publisher query skipped "
            "(starts automatically when you run ros2 commands in rosmac shell)"
        )

    return r

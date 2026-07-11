"""rosmac sim — 선언적 프리셋(YAML)로 VM 시뮬 스택을 tmux 세션으로 기동/관리.

프리셋 위치: 패키지 assets/presets/*.yaml + 사용자 ~/.rosmac/presets/*.yaml (동명이면 사용자 우선).
tmux인 이유: --attach 로그 관찰, 세션 유지, 이중 실행 감지 (phase2 2.2).
"""

import time
from importlib import resources
from pathlib import Path

import yaml
from pydantic import BaseModel

from rosmac import bridge, conda, lima
from rosmac.config import Config
from rosmac.errors import RosmacError

SESSION = "rosmac-sim"
SIM_LOG = "/tmp/rosmac-sim.log"
USER_PRESET_DIR = Path.home() / ".rosmac" / "presets"


class HealthTopic(BaseModel):
    name: str
    timeout: int = 30


class Launch(BaseModel):
    cmd: str


class Preset(BaseModel):
    name: str
    description: str = ""
    vm_apt: list[str] = []
    vm_env: dict[str, str] = {}
    launch: Launch
    foxglove_layout: str | None = None
    health_topics: list[HealthTopic] = []


def _asset_preset_dir():
    return resources.files("rosmac") / "assets" / "presets"


def list_presets() -> dict[str, str]:
    """{이름: 설명}. 사용자 프리셋이 패키지 프리셋을 가린다."""
    out: dict[str, str] = {}
    entries = list(_asset_preset_dir().iterdir()) if _asset_preset_dir().is_dir() else []
    for src in (
        entries,
        sorted(USER_PRESET_DIR.glob("*.yaml")) if USER_PRESET_DIR.is_dir() else [],
    ):
        for f in src:
            name = Path(str(f)).stem
            if not str(f).endswith(".yaml"):
                continue
            try:
                doc = yaml.safe_load(f.read_text()) or {}
                out[name] = doc.get("description", "")
            except Exception:  # noqa: BLE001 — 목록 표시는 최대한 관대하게
                out[name] = "(parse failed)"
    return out


def load_preset(name: str) -> Preset:
    user = USER_PRESET_DIR / f"{name}.yaml"
    if user.exists():
        return Preset.model_validate(yaml.safe_load(user.read_text()))
    pkg = _asset_preset_dir() / f"{name}.yaml"
    if pkg.is_file():
        return Preset.model_validate(yaml.safe_load(pkg.read_text()))
    available = ", ".join(sorted(list_presets())) or "(none)"
    raise KeyError(f"preset '{name}' not found. Available: {available}")


def session_alive(cfg: Config) -> bool:
    try:
        out = lima.shell(
            cfg.vm.name, f"tmux has-session -t {SESSION} 2>/dev/null && echo yes || echo no"
        )
    except RuntimeError:
        return False
    return "yes" in out


def ensure_apt(cfg: Config, packages: list[str], progress=None) -> list[str]:
    """미설치 패키지만 설치. 설치한 목록 반환 (멱등: dpkg -s 확인)."""
    installed: list[str] = []
    for pkg in packages:
        ok = lima.shell(
            cfg.vm.name, f"dpkg -s {pkg} >/dev/null 2>&1 && echo yes || echo no"
        ).strip()
        if ok == "yes":
            continue
        if progress:
            progress(f"apt install: {pkg}")
        lima.shell(
            cfg.vm.name,
            f"sudo DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg}",
            timeout=900,
        )
        installed.append(pkg)
    return installed


def _push_preset_assets(cfg: Config, preset: Preset) -> None:
    """assets/presets/<name>/ 디렉토리가 있으면 VM ~/rosmac-presets/<name>/으로 전송."""
    d = _asset_preset_dir() / preset.name
    if not d.is_dir():
        return
    for f in d.iterdir():
        if f.is_file():
            lima.push(
                cfg.vm.name,
                f.read_text(),
                f"~/rosmac-presets/{preset.name}/{Path(str(f)).name}",
            )


def _reset_mac_bridge(cfg: Config) -> None:
    """VM 브리지 재기동 후 맥 브리지의 낡은 라우트를 재기동으로 정리 (N2 실측 플로우)."""
    if bridge.is_running():
        bridge.stop()
    bridge.start(cfg)


def _reset_bridge_session(cfg: Config, progress=None) -> None:
    """sim 스택 시작 전에 양측 브리지 세션을 리셋 (KI-17/KI-30 진짜 해법 — S0 실측).

    스택을 재기동해도 VM 브리지는 죽은 스택들의 라우트를 누적해, 새 스택의 액션
    하위 서비스 디스커버리가 맥에서 오염돼 `wait_for_server`가 실패한다(0/6).
    브리지를 리셋하면 신선한 라우트로 동일 스택이 4/4 성공. `rosmac up`의 KI-17
    방지와 동일 패턴. (스코핑은 불필요 — N2/N3에서 통한 건 스코프 적용이 브리지를
    재시작한 부수효과였음.)
    """
    lima.shell(cfg.vm.name, "sudo systemctl restart zenoh-bridge", timeout=30)
    _reset_mac_bridge(cfg)
    if progress:
        progress("✓ bridge session reset (KI-17 — fresh routes for new stack)")


def start(cfg: Config, preset: Preset, progress=None) -> None:
    """tmux 세션으로 launch.cmd 실행. 이미 세션이 있으면 RuntimeError (R6 패턴)."""
    if session_alive(cfg):
        raise RosmacError(
            f"tmux session '{SESSION}' already exists — use rosmac sim status/stop or --attach"
        )
    _push_preset_assets(cfg, preset)
    # 새 스택을 띄우기 전 브리지 세션 리셋 — 이전 스택의 라우트 잔재 제거 (KI-17/KI-30)
    _reset_bridge_session(cfg, progress=progress)
    env_exports = " ".join(
        f"{k}={v}"
        for k, v in {
            "ROS_LOCALHOST_ONLY": "1",
            "ROS_DOMAIN_ID": str(cfg.ros.domain_id),
            "RMW_IMPLEMENTATION": cfg.ros.rmw,
            "CYCLONEDDS_URI": "file:///etc/cyclonedds.xml",  # KI-23
            **preset.vm_env,
        }.items()
    )
    inner = (
        f"source /opt/ros/{cfg.ros.distro}/setup.bash && "
        f"export {env_exports} && "
        f"{preset.launch.cmd} 2>&1 | tee {SIM_LOG}"
    )
    quoted = inner.replace("'", "'\\''")
    lima.shell(cfg.vm.name, f"tmux new-session -d -s {SESSION} '{quoted}'", timeout=30)


def wait_healthy(cfg: Config, preset: Preset, progress=None) -> None:
    """health_topics가 맥에서 전부 보일 때까지 폴링. 실패 시 로그 tail 포함 에러."""
    for ht in preset.health_topics:
        deadline = time.monotonic() + ht.timeout
        while True:
            try:
                topics = conda.run_in_env(cfg, "ros2 topic list", timeout=30)
            except RuntimeError:
                topics = ""
            if ht.name in topics.split():
                if progress:
                    progress(f"✓ {ht.name}")
                break
            if time.monotonic() > deadline:
                tail = ""
                try:
                    tail = lima.shell(cfg.vm.name, f"tail -30 {SIM_LOG} 2>/dev/null || true")
                except RuntimeError:
                    pass
                raise RosmacError(
                    f"health topic {ht.name} not visible within {ht.timeout}s.\n"
                    f"--- VM sim log (last 30 lines) ---\n{tail}"
                )
            time.sleep(2)


def stop(cfg: Config, progress=None) -> bool:
    alive = session_alive(cfg)
    if alive:
        lima.shell(cfg.vm.name, f"tmux kill-session -t {SESSION}", timeout=30)
    # tmux kill 시점에 launch가 시그널 핸들러 등록 전이면 gz/bridge가 고아로 남을 수
    # 있음 (P2.4 실측: gz 2개 → 토픽 2배·기아). 프리셋 관련 잔여 프로세스 청소.
    lima.shell(
        cfg.vm.name,
        'pkill -f "[r]osmac-presets" 2>/dev/null; '
        'pkill -f "[i]gn gazebo" 2>/dev/null; '
        'pkill -f "[p]arameter_bridge" 2>/dev/null; true',
        timeout=30,
    )
    return alive


def status(cfg: Config) -> str:
    if not session_alive(cfg):
        return "stopped"
    out = lima.shell(cfg.vm.name, f"tmux list-sessions | grep {SESSION} || true").strip()
    return out or "stopped"

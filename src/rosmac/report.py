"""rosmac report — 이슈 첨부용 진단 번들 생성 (P5.3 ③).

개인정보 규칙: 수집원은 ~/.rosmac 안의 파일과 진단 명령 출력뿐이다.
홈 밖 파일은 절대 수집하지 않고, 수집 목록을 호출자에게 돌려줘 출력하게 한다.
"""

import json
import platform
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import rosmac
from rosmac import lima
from rosmac import doctor as doctor_mod
from rosmac.config import CONFIG_PATH, Config

MAX_LOG_BYTES = 256 * 1024  # 로그는 파일당 마지막 256KB만 (번들 비대 방지)

_HOST_MASK = "masked-by-report"


def mask_host(text: str, host: str | None) -> str:
    """수집물에서 robot.host를 마스킹 (E.15-R4 프라이버시: 로봇 주소 평문 금지).

    config.yaml·doctor.json·브리지 로그(cmdline/라우트에 엔드포인트 포함) 전부에
    나타날 수 있어 파일별 파싱 대신 번들 전체에 일괄 적용한다. host가 로컬 주소
    (대리 로봇 등)면 무관한 문자열까지 가려질 수 있으나 과마스킹이 안전한 방향.
    """
    if not host:
        return text
    return text.replace(host, _HOST_MASK)


def _cmd(cmd: list[str]) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (p.stdout or p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"(failed: {e})"


def version_matrix(cfg: Config) -> str:
    lines = [
        f"rosmac: {rosmac.__version__}",
        f"python: {platform.python_version()}",
        f"macos: {_cmd(['sw_vers', '-productVersion'])} ({platform.machine()})",
        f"lima: {_cmd(['limactl', '--version'])}",
        f"micromamba: {_cmd(['micromamba', '--version'])}",
        f"zenoh-bridge (pinned): {cfg.bridge.version}",
        f"ros: {cfg.ros.distro} / {cfg.ros.rmw} / domain {cfg.ros.domain_id}",
        f"conda: env '{cfg.conda_env}' / channel {cfg.conda_channel}",
        # D15: 설정 유무만 — 호스트는 프라이버시 원칙상 기재하지 않는다 (E.15-R4)
        f"robot: {f'configured (host masked, port {cfg.robot.port})' if cfg.robot.host else 'not configured'}",
    ]
    return "\n".join(lines) + "\n"


def _vm_units(cfg: Config) -> str:
    try:
        if lima.state(cfg.vm.name) is not lima.VmState.RUNNING:
            return "VM not running — unit status unavailable\n"
        return lima.shell(
            cfg.vm.name,
            "systemctl status zenoh-bridge foxglove-bridge --no-pager -l | tail -80; "
            "echo; journalctl -u zenoh-bridge -n 40 --no-pager",
            timeout=30,
        )
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return f"(query failed: {e})\n"


def collect(cfg: Config, work: Path, rosmac_dir: Path | None = None) -> list[str]:
    """진단 자료를 work 디렉토리에 모으고 상대 경로 목록을 반환한다."""
    rosmac_dir = rosmac_dir or CONFIG_PATH.parent
    names: list[str] = []

    def put(name: str, content: str) -> None:
        (work / name).write_text(mask_host(content, cfg.robot.host))
        names.append(name)

    results = doctor_mod.run_all(cfg)
    put("doctor.json", json.dumps([r._asdict() for r in results], ensure_ascii=False, indent=2))
    put("versions.txt", version_matrix(cfg))
    cfg_file = rosmac_dir / "config.yaml"
    if cfg_file.exists():
        put("config.yaml", cfg_file.read_text())

    # 로그 — ~/.rosmac/log/ 만, 파일당 tail 캡 (개인정보 규칙: 홈 밖 수집 금지)
    log_src = rosmac_dir / "log"
    if log_src.is_dir():
        log_dst = work / "log"
        log_dst.mkdir()
        for f in sorted(log_src.iterdir()):
            if not f.is_file():
                continue
            tail = f.read_bytes()[-MAX_LOG_BYTES:].decode(errors="replace")
            (log_dst / f.name).write_text(mask_host(tail, cfg.robot.host))
            names.append(f"log/{f.name}")

    put("vm-units.txt", _vm_units(cfg))
    return names


def create_bundle(cfg: Config, out_dir: Path | None = None) -> tuple[Path, list[str]]:
    """번들 tar.gz를 만들고 (경로, 수집 목록)을 반환한다."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    root = f"rosmac-report-{stamp}"
    out = (out_dir or Path.cwd()) / f"{root}.tar.gz"
    with tempfile.TemporaryDirectory(prefix="rosmac-report-") as td:
        work = Path(td)
        names = collect(cfg, work)
        with tarfile.open(out, "w:gz") as tar:
            tar.add(work, arcname=root)
    return out, names

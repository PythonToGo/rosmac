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
        (work / name).write_text(content)
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
            (log_dst / f.name).write_bytes(f.read_bytes()[-MAX_LOG_BYTES:])
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

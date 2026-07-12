import shutil
import time

import typer
from rich.console import Console
from rich.table import Table

import rosmac
from rosmac import assets, bridge, conda, lima
from rosmac import deps as depsmod
from rosmac.config import Config, load
from rosmac.errors import RosmacError, UsageError

app = typer.Typer(
    no_args_is_help=True,
    help="ROS2 Humble dev environment for Apple Silicon Macs",
)
console = Console()


def main() -> None:
    """콘솔 스크립트 진입점 — exit code 규약(0/1/2)과 에러 표출의 단일 지점 (P5.2).

    RosmacError → rich 패널(원인+처방), exit_code 그대로 (1 실행 실패 / 2 사용법·설정).
    예상 밖 예외만 traceback (+ 이슈 첨부 안내).
    """
    import sys

    from rich.markup import escape
    from rich.panel import Panel

    try:
        app()
    except RosmacError as e:
        # 메시지는 로그 tail 등 [브래킷] 텍스트가 흔해 escape 필수, hint는 rosmac 소유 마크업
        body = escape(str(e)) + (f"\n\n[bold]Fix:[/] {e.hint}" if e.hint else "")
        console.print(Panel(body, title="rosmac error", border_style="red", expand=False))
        sys.exit(e.exit_code)
    except Exception:
        import traceback

        traceback.print_exc()
        console.print(
            "[red]Unexpected error[/] — run `rosmac doctor`, then open an issue "
            "with the traceback above and a `rosmac report` bundle"
        )
        sys.exit(1)


def _print_version(value: bool) -> None:
    if value:
        console.print(f"rosmac {rosmac.__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    _version: bool = typer.Option(
        False, "--version", callback=_print_version, is_eager=True, help="Print version and exit"
    ),
) -> None:
    """Keep subcommand mode even with a single command (typer behavior)."""


@app.command()
def version() -> None:
    """Print the rosmac version."""
    console.print(f"rosmac {rosmac.__version__}")


def _verify_vm_provisioned(cfg: Config) -> None:
    """limactl start는 provision 실패에도 exit 0 (Phase 0 실측) — 실상태 후검증."""
    out = lima.shell(
        cfg.vm.name,
        "ls /opt/ros/humble/setup.bash && systemctl is-active zenoh-bridge",
        timeout=30,
    )
    if "setup.bash" not in out or "active" not in out:
        raise RosmacError(
            f"VM provisioning incomplete (verification output: {out!r})",
            hint=f"Recommended: limactl delete -f {cfg.vm.name}, then rerun rosmac init",
        )


@app.command()
def init(
    auto: bool = typer.Option(False, "--auto", help="Check and auto-install brew dependencies"),
) -> None:
    """Dependency check → conda env → Mac bridge binary → VM provisioning (all steps idempotent)."""
    cfg = load()
    steps: list[tuple[str, str, float]] = []  # (단계, 결과, 소요초)

    # 1. 의존성 검사
    t0 = time.monotonic()
    missing = [tool for tool in ("brew", "limactl", "micromamba") if not shutil.which(tool)]
    if missing:
        install_hint = {
            "brew": '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
            "limactl": "brew install lima",
            "micromamba": "brew install micromamba",
        }
        if auto and "brew" not in missing:
            import subprocess

            for tool in missing:
                console.print(f"[yellow]--auto: running {install_hint[tool]}…[/]")
                subprocess.run(install_hint[tool].split(), check=True)
            steps.append(("dependencies", "✓ auto-installed", time.monotonic() - t0))
        else:
            raise RosmacError(
                f"Missing dependencies: {', '.join(missing)}",
                hint="Run the following yourself, or `rosmac init --auto`:\n"
                + "\n".join(f"  {install_hint[tool]}" for tool in missing),
            )
    else:
        steps.append(("dependencies", "✓", time.monotonic() - t0))

    # 2. conda env
    t0 = time.monotonic()
    if conda.env_exists(cfg.conda_env):
        steps.append(("conda env", "skipped (already exists)", time.monotonic() - t0))
    else:
        with console.status(
            f"[cyan]Creating RoboStack env '{cfg.conda_env}' (takes a few minutes)…[/]"
        ):
            conda.create_env(cfg)
        steps.append(("conda env", "✓ created", time.monotonic() - t0))

    # 3. 맥 브리지 바이너리
    t0 = time.monotonic()
    installed = bridge.ensure_binary(cfg)
    steps.append(
        (
            "zenoh-bridge (Mac)",
            "✓ downloaded" if installed else "skipped (already exists)",
            time.monotonic() - t0,
        )
    )

    # 4. VM
    t0 = time.monotonic()
    vm_state = lima.state(cfg.vm.name)
    if vm_state is lima.VmState.ABSENT:
        yaml_path = assets.write_lima_yaml(cfg)
        with console.status("[cyan]Provisioning VM (about 10 minutes)…[/]"):
            lima.start(cfg.vm.name, str(yaml_path))
            _verify_vm_provisioned(cfg)
        steps.append(("VM", "✓ provisioned", time.monotonic() - t0))
    else:
        steps.append(("VM", f"skipped (state: {vm_state.value})", time.monotonic() - t0))

    table = Table(title="rosmac init summary")
    table.add_column("Step")
    table.add_column("Result")
    table.add_column("Time", justify="right")
    for name, result, dur in steps:
        table.add_row(name, result, f"{dur:.1f}s")
    console.print(table)


def _start_viz(cfg: Config) -> None:
    """VM foxglove-bridge 기동 + 맥 Foxglove 앱 딥링크 오픈 (2.1)."""
    import glob
    import socket
    import subprocess

    lima.shell(cfg.vm.name, "sudo systemctl start foxglove-bridge", timeout=30)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", cfg.foxglove_port), timeout=2):
                break
        except OSError:
            time.sleep(1)
    else:
        console.print(
            f"[yellow]⚠ port {cfg.foxglove_port} not open — "
            f"limactl shell {cfg.vm.name} -- journalctl -u foxglove-bridge[/]"
        )
        return
    console.print(f"✓ foxglove_bridge active (ws://localhost:{cfg.foxglove_port})")
    if glob.glob("/Applications/Foxglove*.app"):
        subprocess.run(
            [
                "open",
                f"foxglove://open?ds=foxglove-websocket&ds.url=ws://localhost:{cfg.foxglove_port}",
            ],
            check=False,
        )
        console.print("✓ Foxglove app opened (deep link)")
    else:
        console.print(
            "[yellow]Foxglove app not found — install from https://foxglove.dev/download,\n"
            f"  then connect via Open connection → ws://localhost:{cfg.foxglove_port}[/]"
        )


@app.command()
def viz(
    layout: str | None = typer.Option(None, "--layout", help="Preset layout name (panda|diffbot|nav2)"),
) -> None:
    """Connect Foxglove visualization (start VM foxglove_bridge + open app)."""
    cfg = load()
    if lima.state(cfg.vm.name) is not lima.VmState.RUNNING:
        raise RosmacError("VM not running", hint="rosmac up")
    if layout:
        # 실측(P2.5): Foxglove 딥링크는 로컬 레이아웃 파일 지정을 지원하지 않음 —
        # 파일을 ~/.rosmac/layouts/에 놓고 Import 안내로 대체 (phase2 2.5 결정)
        from importlib import resources
        from pathlib import Path

        src = resources.files("rosmac") / "assets" / "layouts" / f"{layout}.json"
        if not src.is_file():
            raise UsageError(f"Layout '{layout}' not found (panda|diffbot|nav2)")
        dest = Path.home() / ".rosmac" / "layouts" / f"{layout}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text())
        console.print(
            f"Layout ready: {dest}\n"
            "In Foxglove, load it via [bold]Layout menu → Import from file…[/] (first time only)"
        )
    _start_viz(cfg)


@app.command()
def up(
    viz: bool = typer.Option(False, "--viz", help="Also connect Foxglove visualization"),
) -> None:
    """Start VM (if stopped) + start Mac bridge + connection smoke test."""
    cfg = load()
    # E.7: pip 업그레이드로 핀이 바뀌었으면 up이 바이너리를 갱신 (구버전 조용히 동작 방지)
    try:
        if bridge.ensure_binary(cfg):
            console.print(f"✓ mac bridge binary installed/updated (v{cfg.bridge.version})")
            if bridge.is_running():
                console.print(
                    "[yellow]⚠ running bridge predates the update — "
                    "restart with: rosmac down --keep-vm && rosmac up[/]"
                )
    except OSError as e:  # 오프라인 등 — 설치돼 있으면 기존 바이너리로 계속 (start가 부재를 처리)
        console.print(
            f"[yellow]⚠ bridge binary update check failed ({e}) — using installed binary[/]"
        )
    vm_state = lima.state(cfg.vm.name)
    if vm_state is lima.VmState.ABSENT:
        raise RosmacError("VM not found", hint="rosmac init")
    if vm_state is lima.VmState.STOPPED:
        with console.status("[cyan]Starting VM…[/]"):
            lima.start(cfg.vm.name, None, timeout=300)
        console.print("✓ VM started")
    else:
        console.print("✓ VM already running")

    vm_bridge = lima.shell(cfg.vm.name, "systemctl is-active zenoh-bridge || true").strip()
    if vm_bridge != "active":
        console.print(f"[yellow]⚠ VM bridge state: {vm_bridge} — run rosmac doctor[/]")
    else:
        console.print("✓ VM bridge active (systemd)")

    if not bridge.is_running() and vm_bridge == "active":
        # 맥 브리지가 죽어 있었다면(정상 down 포함) VM 브리지의 이전 세션 라우트가
        # 남아 있을 수 있음 (KI-17: SIGKILL 잔재 → 토픽 2배 수신). 재시작으로 초기화.
        lima.shell(cfg.vm.name, "sudo systemctl restart zenoh-bridge", timeout=30)
        console.print("✓ VM bridge session reset (KI-17 prevention)")

    if bridge.start(cfg):
        console.print("✓ Mac bridge started")
    else:
        console.print("✓ Mac bridge already running (pidfile)")
        # D15: 브리지가 config 변경(robot 추가/제거) 전에 떴다면 엔드포인트가 어긋남
        cmdline = bridge.running_cmdline() or ""
        if cfg.robot.host and bridge.robot_endpoint(cfg) not in cmdline:
            console.print(
                "[yellow]⚠ running bridge has no robot endpoint — "
                "restart with: rosmac down --keep-vm && rosmac up[/]"
            )

    if cfg.robot.host:
        if bridge.robot_reachable(cfg):
            console.print(f"✓ robot endpoint reachable ({bridge.robot_endpoint(cfg)})")
        else:
            console.print(
                f"[yellow]⚠ robot endpoint {bridge.robot_endpoint(cfg)} unreachable "
                "(robot off? firewall?) — bridge will auto-connect when it appears[/]"
            )

    # 연결 스모크: 브리지 로그에 원격 브리지 감지가 찍히는지 몇 초 대기
    time.sleep(3)
    log = bridge.LOG_PATH.read_text() if bridge.LOG_PATH.exists() else ""
    if "New ROS 2 bridge detected" in log or "Remote bridge" in log:
        console.print("✓ bridges see each other")
    else:
        console.print("[yellow]⚠ no mutual bridge detection in logs — rosmac doctor recommended[/]")

    if viz:
        _start_viz(cfg)


@app.command()
def down(
    keep_vm: bool = typer.Option(False, "--keep-vm", help="Stop only the bridge, keep the VM"),
) -> None:
    """Stop the Mac bridge (SIGTERM), then stop the VM."""
    cfg = load()
    if bridge.stop():
        console.print("✓ Mac bridge stopped")
    else:
        console.print("- Mac bridge not running")
    if keep_vm:
        return
    if lima.state(cfg.vm.name) is lima.VmState.RUNNING:
        with console.status("[cyan]Stopping VM…[/]"):
            lima.stop(cfg.vm.name)
        console.print("✓ VM stopped")
    else:
        console.print("- VM not running")


@app.command()
def doctor(
    json_out: bool = typer.Option(False, "--json", help="Output JSON (for automation)"),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Apply safe automatic fixes first (daemon restart, orphan sweep, lima rules)",
    ),
) -> None:
    """Run C1~C17 checks. With --fix, apply safe fixes first. Exit 1 if any check FAILs."""
    from rosmac import doctor as doctor_mod

    cfg = load()
    fixes: list[doctor_mod.FixResult] = []
    if fix:
        fixes = doctor_mod.fix_all(cfg)
        if not json_out:
            for f in fixes:
                mark = "[green]✓[/]" if f.applied else "-"
                console.print(f"{mark} {f.name}: {f.detail}")
    results = doctor_mod.run_all(cfg)
    if json_out:
        import json as json_lib

        checks = [r._asdict() for r in results]
        if fix:  # --fix 없인 기존 스키마(리스트) 유지 — 자동화 호환
            print(
                json_lib.dumps(
                    {"fixes": [f._asdict() for f in fixes], "checks": checks},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(json_lib.dumps(checks, ensure_ascii=False, indent=2))
    else:
        table = Table(title="rosmac doctor")
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Detail")
        table.add_column("Fix")
        style = {"PASS": "green", "WARN": "yellow", "FAIL": "red", "SKIP": "dim"}
        for r in results:
            table.add_row(r.name, f"[{style[r.status]}]{r.status}[/]", r.detail, r.remedy or "")
        console.print(table)
    if any(r.status == "FAIL" for r in results):
        raise typer.Exit(1)


@app.command()
def shell(
    vm: bool = typer.Option(False, "--vm", help="Enter the VM shell instead of the Mac"),
    command: str | None = typer.Option(
        None, "-c", help="Run a single command instead of a shell (for E2E)"
    ),
) -> None:
    """Open a subshell with the ROS env injected (micromamba activate + ROS_* env)."""
    import os
    import subprocess
    import tempfile

    cfg = load()
    if vm:
        if command:
            # bash -lc는 .bashrc의 ROS 소싱에 도달 못 함 (KI-19) → 명시 소싱 + env 주입
            wrapped = (
                f"source /opt/ros/{cfg.ros.distro}/setup.bash; "
                f"export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID={cfg.ros.domain_id} "
                f"RMW_IMPLEMENTATION={cfg.ros.rmw} "
                f"CYCLONEDDS_URI=file:///etc/cyclonedds.xml; {command}"
            )
            print(lima.shell(cfg.vm.name, wrapped, timeout=300), end="")
            return
        os.execvp("limactl", ["limactl", "shell", cfg.vm.name])

    if command:
        print(conda.run_in_env(cfg, command, timeout=300), end="")
        return

    # 인터랙티브: 임시 ZDOTDIR의 .zshrc로 env 주입 (부록 C-5)
    tmpdir = tempfile.mkdtemp(prefix="rosmac-shell-")
    zshrc = os.path.join(tmpdir, ".zshrc")
    with open(zshrc, "w") as f:
        f.write(
            "source ~/.zshrc 2>/dev/null\n"
            'eval "$(micromamba shell hook -s zsh)" 2>/dev/null\n'
            f"export MAMBA_ROOT_PREFIX=${{MAMBA_ROOT_PREFIX:-$HOME/micromamba}}\n"
            f"micromamba activate {cfg.conda_env}\n"
            "export ROS_LOCALHOST_ONLY=1\n"
            f"export ROS_DOMAIN_ID={cfg.ros.domain_id}\n"
            f"export RMW_IMPLEMENTATION={cfg.ros.rmw}\n"
            f"export ROS_DISTRO={cfg.ros.distro}\n"
            f"export CYCLONEDDS_URI={assets.ensure_mac_cyclonedds()}\n"
            + (
                f"export COLCON_DEFAULTS_FILE={assets.ensure_colcon_defaults()}\n"  # KI-25
                if cfg.build.colcon_defaults
                else ""
            )
            + 'export PS1="(rosmac) $PS1"\n'
        )
    env = dict(os.environ, ZDOTDIR=tmpdir)
    raise typer.Exit(subprocess.run(["zsh", "-i"], env=env).returncode)


@app.command()
def push(
    ws: str = typer.Argument(".", help="colcon workspace root (directory containing src/)"),
    name: str | None = typer.Option(
        None, "--name", help="Workspace name on the VM (default: directory name)"
    ),
    build: bool = typer.Option(False, "--build", help="Also run colcon build on the VM after push"),
) -> None:
    # P4.4/D14
    """Copy workspace src/ to VM ~/rosmac-ws/<name>/ (for packages that don't build on the Mac)."""
    import re
    from pathlib import Path

    cfg = load()
    root = Path(ws).expanduser().resolve()
    if not (root / "src").is_dir():
        raise UsageError(f"No src/ in {root} — point to a colcon workspace root")
    ws_name = name or root.name
    if not re.fullmatch(r"[A-Za-z0-9_-]+", ws_name):
        raise UsageError(f"Invalid workspace name: {ws_name!r} (alphanumeric/_/- only)")
    if lima.state(cfg.vm.name) is not lima.VmState.RUNNING:
        raise RosmacError("VM not running", hint="rosmac up")

    dest = f"~/rosmac-ws/{ws_name}/src"
    console.print(f"Push: {root}/src → VM {dest}")
    try:
        lima.push_tree(cfg.vm.name, str(root / "src"), dest)
    except ValueError as e:
        raise UsageError(str(e)) from None
    console.print("[green]✓ push complete[/] (re-running replaces the VM-side src entirely)")

    if build:
        console.print("Running colcon build on the VM…")
        # KI-19: 비인터랙티브 셸은 ROS 소싱이 안 됨 — 명시적 source 필수
        build_cmd = (
            f"source /opt/ros/{cfg.ros.distro}/setup.bash && "
            f"cd ~/rosmac-ws/{ws_name} && colcon build --symlink-install 2>&1 | tail -15"
        )
        try:
            print(lima.shell(cfg.vm.name, build_cmd, timeout=1800), end="")
        except RuntimeError as e:
            raise RosmacError(
                f"VM build failed: {e}",
                hint="If apt dependencies are needed, the VM is standard Ubuntu so rosdep works:\n"
                f"  rosmac shell --vm  →  cd ~/rosmac-ws/{ws_name} && "
                "rosdep install --from-paths src -y",
            ) from None
    console.print(
        f"Run: [bold]rosmac shell --vm[/] → "
        f"source ~/rosmac-ws/{ws_name}/install/setup.bash → ros2 run …\n"
        "(topics are visible on the Mac via the zenoh bridge)"
    )


@app.command()
def ps(
    json_out: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    # P4.3
    """ROS processes and core topic publishers on Mac+VM, one screen (first-line diagnosis)."""
    import json as _json

    from rosmac import psview

    cfg = load()
    report = psview.collect(cfg)
    if json_out:
        print(_json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
        return

    console.print("[bold]── Mac ──[/]")
    d = report.daemon
    daemon_str = (
        "not started"
        if d.pid is None
        else f"PID {d.pid}  "
        + (f"responsive ✓ ({d.latency_ms}ms)" if d.responsive else "[red]no response (hang)[/]")
    )
    console.print(f"  ros2 daemon    {daemon_str}")
    console.print(
        "  zenoh-bridge   "
        + (f"PID {report.bridge_pid} (pidfile match)" if report.bridge_pid else "not started")
    )
    for o in report.orphan_bridges:
        console.print(f"  [yellow]⚠ orphan bridge[/] PID {o.pid}")
    if report.mac_nodes:
        console.print("  ROS processes:")
        for p in report.mac_nodes:
            console.print(f"    {p.pid:>7}  {p.command}")
    else:
        console.print("  ROS processes: none")

    if report.robot_link:  # robot 미설정이면 섹션 자체를 생략 (D15)
        rl = report.robot_link
        reach = "reachable ✓" if rl.reachable else "[yellow]unreachable (robot off? firewall?)[/]"
        in_args = {True: "in bridge args ✓", False: "[yellow]NOT in bridge args[/]", None: ""}[
            rl.in_bridge_args
        ]
        console.print("[bold]── Robot link ──[/]")
        console.print(f"  {rl.endpoint}   {reach}   {in_args}".rstrip())

    console.print(f"[bold]── VM ({cfg.vm.name}: {report.vm_state}) ──[/]")
    if report.vm_units:
        units = "   ".join(f"{k} {v}" for k, v in report.vm_units.items())
        console.print(f"  {units}   sim session: {'yes' if report.vm_sim_session else 'no'}")
    for p in report.vm_ros_procs:
        console.print(f"    {p.pid:>7}  {p.command}")

    console.print("[bold]── Graph (core topic publishers) ──[/]")
    if report.graph_note:
        console.print(f"  {report.graph_note}")
    for t in report.core_topics:
        mark = "[yellow]⚠[/] " if t.warning else ""
        console.print(
            f"  {mark}{t.topic}  publishers {len(t.publishers)}: {', '.join(t.publishers) or '-'}"
        )

    if report.warnings:
        console.print("[bold yellow]── Warnings ──[/]")
        for w in report.warnings:
            console.print(f"  ⚠ {w}")


@app.command()
def deps(
    ws: str = typer.Argument(".", help="colcon workspace root (directory containing src/)"),
    install: bool = typer.Option(False, "--install", help="Install the missing bucket immediately"),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    # P4.2
    """Check package.xml dependencies against RoboStack conda packages (rosdep replacement on the Mac)."""
    import json as _json
    from pathlib import Path

    cfg = load()
    root = Path(ws).expanduser().resolve()
    if not (root / "src").is_dir():
        raise UsageError(f"No src/ in {root} — point to a colcon workspace root")
    report = depsmod.analyze(cfg, root)
    if install and report.missing:
        if not json_out:  # --json일 땐 stdout을 JSON만으로 유지 (파이프 안전)
            console.print(f"Installing: {', '.join(report.missing)}")
        depsmod.install_missing(cfg, report.missing)
        report = depsmod.analyze(cfg, root)  # 재분석으로 설치 결과 검증

    if json_out:
        print(_json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
        return
    table = Table(title=f"rosmac deps — {root}")
    table.add_column("Bucket")
    table.add_column("Packages")
    table.add_row("installed", ", ".join(report.installed) or "-")
    table.add_row("[yellow]missing[/]", ", ".join(report.missing) or "-")
    table.add_row("[red]unknown[/]", ", ".join(report.unknown) or "-")
    table.add_row("[red]unavailable[/]", ", ".join(report.unavailable) or "-")
    table.add_row("(in workspace)", ", ".join(report.skipped_local) or "-")
    console.print(table)
    if report.missing:
        console.print(
            f"[yellow]→ rosmac deps {ws} --install[/] or:\n"
            f"  micromamba install -n {cfg.conda_env} -c conda-forge "
            f"-c {cfg.conda_channel} {' '.join(report.missing)}"
        )
    if report.unknown:
        console.print(
            "[red]unknown[/]: mapping uncertain — may be a system dependency. "
            "Find the name on conda-forge and install manually; if you figure out "
            "the mapping, please contribute it to SPECIAL_MAP in deps.py"
        )


@app.command()
def sim(
    name: str = typer.Argument(..., help="Preset name, or stop|status|list"),
    attach: bool = typer.Option(False, "--attach", help="Attach to the tmux session to watch logs"),
    no_viz: bool = typer.Option(False, "--no-viz", help="Do not open Foxglove after READY"),
) -> None:
    """Start a sim preset on the VM (tmux) → poll health → open Foxglove when READY."""
    import os

    from rosmac import doctor as doctor_mod
    from rosmac import sim as sim_mod

    cfg = load()

    if name == "list":
        table = Table(title="rosmac sim presets")
        table.add_column("Name")
        table.add_column("Description")
        for n, desc in sorted(sim_mod.list_presets().items()):
            table.add_row(n, desc)
        console.print(table)
        return
    if name == "stop":
        console.print("✓ sim session stopped" if sim_mod.stop(cfg) else "- no sim session running")
        return
    if name == "status":
        console.print(sim_mod.status(cfg))
        return
    if attach:
        os.execvp(
            "limactl",
            ["limactl", "shell", cfg.vm.name, "--", "tmux", "attach", "-t", sim_mod.SESSION],
        )

    try:
        preset = sim_mod.load_preset(name)
    except KeyError as e:
        raise UsageError(e.args[0], hint="rosmac sim list") from None

    # 사전 점검 (C2 VM, C5 포트, C6 맥 브리지, C7 VM 브리지 — C8은 느려서 제외)
    pre = [c for c in doctor_mod.CHECKS if c.name.split()[0] in ("C2", "C5", "C6", "C7")]
    failed = [r for r in (c.run(cfg) for c in pre) if r.status == "FAIL"]
    if failed:
        raise RosmacError(
            "\n".join(f"{r.name}: {r.detail}" for r in failed),
            # 같은 처방(rosmac up 등)이 체크마다 반복되므로 순서 보존 중복 제거
            hint="\n".join(dict.fromkeys(r.remedy for r in failed if r.remedy)),
        )

    installed = sim_mod.ensure_apt(cfg, preset.vm_apt, progress=lambda m: console.print(f"  {m}"))
    if installed:
        console.print(f"✓ VM packages installed: {', '.join(installed)}")
    # 맥 env msg 의존 (맥에서 액션 goal 보내는 데 필요 — 없으면 goal 침묵 실패, E.20)
    mac_pkgs = depsmod.ensure_installed(
        cfg, preset.mac_env_pkgs, progress=lambda m: console.print(f"  {m}")
    )
    if mac_pkgs:
        console.print(f"✓ Mac env packages installed: {', '.join(mac_pkgs)}")
    sim_mod.start(cfg, preset)
    console.print(f"✓ tmux session '{sim_mod.SESSION}' started — logs: rosmac sim --attach")
    with console.status("[cyan]waiting for health topics…[/]"):
        try:
            sim_mod.wait_healthy(cfg, preset, progress=lambda m: console.print(f"  {m}"))
        except RuntimeError as e:
            sim_mod.stop(cfg)  # 실패 시 세션 정리 후 보고 (main이 escape 처리)
            raise RosmacError(str(e)) from None
    console.print("[green bold]READY[/]")
    if not no_viz:
        _start_viz(cfg)


@app.command()
def status() -> None:
    """Status table: VM / bridges / port / conda env."""
    cfg = load()
    table = Table(title="rosmac status")
    table.add_column("Item")
    table.add_column("Status")

    vm_state = lima.state(cfg.vm.name)
    table.add_row("VM", vm_state.value)

    if vm_state is lima.VmState.RUNNING:
        vm_bridge = lima.shell(cfg.vm.name, "systemctl is-active zenoh-bridge || true").strip()
    else:
        vm_bridge = "-"
    table.add_row("VM bridge (systemd)", vm_bridge)

    table.add_row("Mac bridge", "running" if bridge.is_running() else "stopped")

    import socket

    try:
        with socket.create_connection(("127.0.0.1", cfg.bridge.port), timeout=2):
            port_ok = "open"
    except OSError:
        port_ok = "closed"
    table.add_row(f"Port {cfg.bridge.port}", port_ok)

    if cfg.robot.host:
        robot_state = "reachable" if bridge.robot_reachable(cfg) else "unreachable"
        table.add_row(f"Robot ({bridge.robot_endpoint(cfg)})", robot_state)
    else:
        table.add_row("Robot", "not configured")

    table.add_row("conda env", cfg.conda_env if conda.env_exists(cfg.conda_env) else "none")
    console.print(table)


@app.command()
def report() -> None:
    """Create a diagnostic bundle for issue reports (rosmac-report-<date>.tar.gz)."""
    from rosmac import report as report_mod

    cfg = load()
    console.print("Collecting diagnostics (runs full doctor — about a minute)…")
    path, names = report_mod.create_bundle(cfg)
    console.print("Collected (only from ~/.rosmac and command output — nothing else):")
    for n in names:
        console.print(f"  {n}")
    console.print(f"[green]✓ {path}[/] — attach this file to your issue")


def _kill_ros2_daemon() -> None:
    """제거될 env 소속의 ros2 데몬 정리 (없으면 no-op).

    SIGKILL을 쓴다 — 실측(P5.2): 데몬이 SIGTERM을 무시하고 생존, env 삭제 후
    좀비 잔재가 됨. 데몬은 무상태 캐시라 강제 종료가 안전하다.
    """
    import subprocess

    subprocess.run(["pkill", "-9", "-f", "ros2cli.daemon"], capture_output=True)


@app.command()
def uninstall(
    yes: bool = typer.Option(False, "--yes", help="Remove everything without confirmation"),
) -> None:
    # 절대 규칙 7: 각 대상을 경로/명령과 함께 출력하고 개별 확인 후 제거한다.
    """Remove what rosmac created: conda env → VM → ~/.rosmac (brew tools and Foxglove app: guidance only)."""
    import shutil as shutil_mod
    from collections.abc import Callable

    from rosmac.config import CONFIG_PATH

    cfg = load()

    # 실행 중인 것 먼저 정리 (제거 대상에 pidfile·env 프로세스가 얽혀 있음)
    if bridge.stop():
        console.print("✓ Mac bridge stopped")
    _kill_ros2_daemon()

    targets: list[tuple[str, Callable[[], None]]] = []  # (설명, 제거 액션)
    if conda.env_exists(cfg.conda_env):
        targets.append(
            (
                f"conda env '{cfg.conda_env}' (micromamba env remove -y -n {cfg.conda_env})",
                lambda: conda.remove_env(cfg),
            )
        )
    if lima.state(cfg.vm.name) is not lima.VmState.ABSENT:
        targets.append(
            (
                f"VM '{cfg.vm.name}' (limactl delete -f {cfg.vm.name})",
                lambda: lima.delete(cfg.vm.name),
            )
        )
    rosmac_dir = CONFIG_PATH.parent
    if rosmac_dir.exists():
        targets.append((f"{rosmac_dir} (rm -rf)", lambda: shutil_mod.rmtree(rosmac_dir)))

    if not targets:
        console.print("- nothing to remove (already clean)")
    for label, action in targets:
        if not yes and not typer.confirm(f"Remove: {label}?"):
            console.print(f"- skipped: {label}")
            continue
        action()
        console.print(f"✓ removed: {label}")

    console.print(
        "\nRemaining (not owned by rosmac — remove yourself):\n"
        "  brew uninstall lima micromamba   (other projects may use them)\n"
        "  Foxglove app (/Applications)\n"
        "  this repo clone and .venv"
    )

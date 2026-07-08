import shutil
import time

import typer
from rich.console import Console
from rich.table import Table

import rosmac
from rosmac import assets, bridge, conda, lima
from rosmac import deps as depsmod
from rosmac.config import Config, load

app = typer.Typer(
    no_args_is_help=True,
    help="ROS2 Humble dev environment for Apple Silicon Macs",
)
console = Console()


@app.callback()
def _main() -> None:
    """커맨드가 1개뿐이어도 서브커맨드 모드를 유지한다 (typer 특성)."""


@app.command()
def version() -> None:
    """rosmac 버전을 출력한다."""
    console.print(f"rosmac {rosmac.__version__}")


def _verify_vm_provisioned(cfg: Config) -> None:
    """limactl start는 provision 실패에도 exit 0 (Phase 0 실측) — 실상태 후검증."""
    out = lima.shell(
        cfg.vm.name,
        "ls /opt/ros/humble/setup.bash && systemctl is-active zenoh-bridge",
        timeout=30,
    )
    if "setup.bash" not in out or "active" not in out:
        raise RuntimeError(
            f"VM 프로비저닝 불완전 (검증 출력: {out!r}). "
            f"limactl delete -f {cfg.vm.name} 후 rosmac init 재실행을 권장"
        )


@app.command()
def init(
    auto: bool = typer.Option(False, "--auto", help="brew 의존성을 확인 후 자동 설치"),
) -> None:
    """의존성 검사 → conda env → 맥 브리지 바이너리 → VM 프로비저닝 (전 단계 멱등)."""
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
                console.print(f"[yellow]--auto: {install_hint[tool]} 실행 중…[/]")
                subprocess.run(install_hint[tool].split(), check=True)
            steps.append(("의존성", "✓ 자동 설치", time.monotonic() - t0))
        else:
            console.print("[red]누락된 의존성이 있습니다. 아래를 직접 실행하세요:[/]")
            for tool in missing:
                console.print(f"  {install_hint[tool]}")
            raise typer.Exit(1)
    else:
        steps.append(("의존성", "✓", time.monotonic() - t0))

    # 2. conda env
    t0 = time.monotonic()
    if conda.env_exists(cfg.conda_env):
        steps.append(("conda env", "스킵 (이미 존재)", time.monotonic() - t0))
    else:
        with console.status(f"[cyan]RoboStack env '{cfg.conda_env}' 생성 중 (수 분 소요)…[/]"):
            conda.create_env(cfg)
        steps.append(("conda env", "✓ 생성", time.monotonic() - t0))

    # 3. 맥 브리지 바이너리
    t0 = time.monotonic()
    installed = bridge.ensure_binary(cfg)
    steps.append(("zenoh-bridge(맥)", "✓ 다운로드" if installed else "스킵 (이미 존재)",
                  time.monotonic() - t0))

    # 4. VM
    t0 = time.monotonic()
    vm_state = lima.state(cfg.vm.name)
    if vm_state is lima.VmState.ABSENT:
        yaml_path = assets.write_lima_yaml(cfg)
        with console.status("[cyan]VM 프로비저닝 중 (10분 내외 소요)…[/]"):
            lima.start(cfg.vm.name, str(yaml_path))
            _verify_vm_provisioned(cfg)
        steps.append(("VM", "✓ 프로비저닝", time.monotonic() - t0))
    else:
        steps.append(("VM", f"스킵 (상태: {vm_state.value})", time.monotonic() - t0))

    table = Table(title="rosmac init 요약")
    table.add_column("단계")
    table.add_column("결과")
    table.add_column("소요", justify="right")
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
        console.print(f"[yellow]⚠ 포트 {cfg.foxglove_port} 미개방 — "
                      f"limactl shell {cfg.vm.name} -- journalctl -u foxglove-bridge[/]")
        return
    console.print(f"✓ foxglove_bridge active (ws://localhost:{cfg.foxglove_port})")
    if glob.glob("/Applications/Foxglove*.app"):
        subprocess.run(
            ["open", f"foxglove://open?ds=foxglove-websocket&ds.url=ws://localhost:{cfg.foxglove_port}"],
            check=False,
        )
        console.print("✓ Foxglove 앱 오픈 (딥링크)")
    else:
        console.print(
            "[yellow]Foxglove 앱이 없습니다 — https://foxglove.dev/download 에서 설치 후\n"
            f"  Open connection → ws://localhost:{cfg.foxglove_port} 로 접속하세요[/]"
        )


@app.command()
def viz(
    layout: str | None = typer.Option(None, "--layout", help="프리셋 레이아웃 이름 (panda|diffbot)"),
) -> None:
    """Foxglove 시각화 연결 (VM foxglove_bridge 기동 + 앱 오픈)."""
    cfg = load()
    if lima.state(cfg.vm.name) is not lima.VmState.RUNNING:
        console.print("[red]VM이 실행 중이 아닙니다 — 먼저 `rosmac up`[/]")
        raise typer.Exit(1)
    if layout:
        # 실측(P2.5): Foxglove 딥링크는 로컬 레이아웃 파일 지정을 지원하지 않음 —
        # 파일을 ~/.rosmac/layouts/에 놓고 Import 안내로 대체 (phase2 2.5 결정)
        from importlib import resources
        from pathlib import Path

        src = resources.files("rosmac") / "assets" / "layouts" / f"{layout}.json"
        if not src.is_file():
            console.print(f"[red]레이아웃 '{layout}' 없음 (panda|diffbot)[/]")
            raise typer.Exit(1)
        dest = Path.home() / ".rosmac" / "layouts" / f"{layout}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text())
        console.print(
            f"레이아웃 준비됨: {dest}\n"
            "Foxglove에서 [bold]Layout 메뉴 → Import from file…[/] 로 불러오세요 (최초 1회)"
        )
    _start_viz(cfg)


@app.command()
def up(viz: bool = typer.Option(False, "--viz", help="Foxglove 시각화도 함께 연결")) -> None:
    """VM 기동(정지 시) + 맥 브리지 기동 + 연결 스모크."""
    cfg = load()
    vm_state = lima.state(cfg.vm.name)
    if vm_state is lima.VmState.ABSENT:
        console.print("[red]VM이 없습니다 — 먼저 `rosmac init`을 실행하세요[/]")
        raise typer.Exit(1)
    if vm_state is lima.VmState.STOPPED:
        with console.status("[cyan]VM 기동 중…[/]"):
            lima.start(cfg.vm.name, None, timeout=300)
        console.print("✓ VM 기동")
    else:
        console.print("✓ VM 이미 실행 중")

    vm_bridge = lima.shell(cfg.vm.name, "systemctl is-active zenoh-bridge || true").strip()
    if vm_bridge != "active":
        console.print(f"[yellow]⚠ VM 브리지 상태: {vm_bridge} — rosmac doctor로 진단하세요[/]")
    else:
        console.print("✓ VM 브리지 active (systemd)")

    if not bridge.is_running() and vm_bridge == "active":
        # 맥 브리지가 죽어 있었다면(정상 down 포함) VM 브리지의 이전 세션 라우트가
        # 남아 있을 수 있음 (KI-17: SIGKILL 잔재 → 토픽 2배 수신). 재시작으로 초기화.
        lima.shell(cfg.vm.name, "sudo systemctl restart zenoh-bridge", timeout=30)
        console.print("✓ VM 브리지 세션 초기화 (KI-17 예방)")

    if bridge.start(cfg):
        console.print("✓ 맥 브리지 기동")
    else:
        console.print("✓ 맥 브리지 이미 실행 중 (pidfile)")

    # 연결 스모크: 브리지 로그에 원격 브리지 감지가 찍히는지 몇 초 대기
    time.sleep(3)
    log = bridge.LOG_PATH.read_text() if bridge.LOG_PATH.exists() else ""
    if "New ROS 2 bridge detected" in log or "Remote bridge" in log:
        console.print("✓ 브리지 상호 감지 확인")
    else:
        console.print("[yellow]⚠ 브리지 상호 감지 로그 미확인 — rosmac doctor 권장[/]")

    if viz:
        _start_viz(cfg)


@app.command()
def down(
    keep_vm: bool = typer.Option(False, "--keep-vm", help="브리지만 내리고 VM은 유지"),
) -> None:
    """맥 브리지 종료(SIGTERM) 후 VM 정지."""
    cfg = load()
    if bridge.stop():
        console.print("✓ 맥 브리지 종료")
    else:
        console.print("- 맥 브리지 실행 중 아님")
    if keep_vm:
        return
    if lima.state(cfg.vm.name) is lima.VmState.RUNNING:
        with console.status("[cyan]VM 정지 중…[/]"):
            lima.stop(cfg.vm.name)
        console.print("✓ VM 정지")
    else:
        console.print("- VM 실행 중 아님")


@app.command()
def doctor(
    json_out: bool = typer.Option(False, "--json", help="JSON으로 출력 (자동화용)"),
) -> None:
    """C1~C11 진단. FAIL이 하나라도 있으면 exit 1."""
    from rosmac import doctor as doctor_mod

    cfg = load()
    results = doctor_mod.run_all(cfg)
    if json_out:
        import json as json_lib

        print(json_lib.dumps([r._asdict() for r in results], ensure_ascii=False, indent=2))
    else:
        table = Table(title="rosmac doctor")
        table.add_column("검사")
        table.add_column("판정")
        table.add_column("상세")
        table.add_column("처방")
        style = {"PASS": "green", "WARN": "yellow", "FAIL": "red"}
        for r in results:
            table.add_row(r.name, f"[{style[r.status]}]{r.status}[/]", r.detail, r.remedy or "")
        console.print(table)
    if any(r.status == "FAIL" for r in results):
        raise typer.Exit(1)


@app.command()
def shell(
    vm: bool = typer.Option(False, "--vm", help="맥 대신 VM 셸로 진입"),
    command: str | None = typer.Option(None, "-c", help="셸 대신 단일 명령 실행 (E2E용)"),
) -> None:
    """ROS env가 주입된 서브셸을 연다 (micromamba activate + ROS_* env)."""
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
        try:
            print(conda.run_in_env(cfg, command, timeout=300), end="")
        except RuntimeError as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(1) from None
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
def ps(
    json_out: bool = typer.Option(False, "--json", help="기계 판독용 JSON 출력"),
) -> None:
    """맥+VM의 ROS 프로세스·핵심 토픽 발행자를 한 화면에 (P4.3, 장애 1차 진단용)."""
    import json as _json

    from rosmac import psview

    cfg = load()
    report = psview.collect(cfg)
    if json_out:
        print(_json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
        return

    console.print("[bold]── 맥 ──[/]")
    d = report.daemon
    daemon_str = (
        "미기동"
        if d.pid is None
        else f"PID {d.pid}  " + (f"응답 ✓ ({d.latency_ms}ms)" if d.responsive else "[red]응답 없음(hang)[/]")
    )
    console.print(f"  ros2 daemon    {daemon_str}")
    console.print(
        f"  zenoh-bridge   "
        + (f"PID {report.bridge_pid} (pidfile 일치)" if report.bridge_pid else "미기동")
    )
    for o in report.orphan_bridges:
        console.print(f"  [yellow]⚠ 고아 브리지[/] PID {o.pid}")
    if report.mac_nodes:
        console.print("  ROS 프로세스:")
        for p in report.mac_nodes:
            console.print(f"    {p.pid:>7}  {p.command}")
    else:
        console.print("  ROS 프로세스: 없음")

    console.print(f"[bold]── VM ({cfg.vm.name}: {report.vm_state}) ──[/]")
    if report.vm_units:
        units = "   ".join(f"{k} {v}" for k, v in report.vm_units.items())
        console.print(f"  {units}   sim 세션: {'있음' if report.vm_sim_session else '없음'}")
    for p in report.vm_ros_procs:
        console.print(f"    {p.pid:>7}  {p.command}")

    console.print("[bold]── 그래프 (핵심 토픽 발행자) ──[/]")
    if report.graph_note:
        console.print(f"  {report.graph_note}")
    for t in report.core_topics:
        mark = "[yellow]⚠[/] " if t.warning else ""
        console.print(f"  {mark}{t.topic}  발행자 {len(t.publishers)}: {', '.join(t.publishers) or '-'}")

    if report.warnings:
        console.print("[bold yellow]── 경고 ──[/]")
        for w in report.warnings:
            console.print(f"  ⚠ {w}")


@app.command()
def deps(
    ws: str = typer.Argument(".", help="colcon 워크스페이스 루트 (src/ 포함 디렉토리)"),
    install: bool = typer.Option(False, "--install", help="missing 버킷을 즉시 설치"),
    json_out: bool = typer.Option(False, "--json", help="기계 판독용 JSON 출력"),
) -> None:
    """package.xml 의존성 → RoboStack conda 패키지 점검 (맥에서 rosdep 대체, P4.2)."""
    import json as _json
    from pathlib import Path

    cfg = load()
    root = Path(ws).expanduser().resolve()
    if not (root / "src").is_dir():
        console.print(f"[red]{root}에 src/가 없음 — colcon 워크스페이스 루트를 지정하세요[/]")
        raise typer.Exit(2)
    try:
        report = depsmod.analyze(cfg, root)
        if install and report.missing:
            if not json_out:  # --json일 땐 stdout을 JSON만으로 유지 (파이프 안전)
                console.print(f"설치 중: {', '.join(report.missing)}")
            depsmod.install_missing(cfg, report.missing)
            report = depsmod.analyze(cfg, root)  # 재분석으로 설치 결과 검증
    except RuntimeError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1) from None

    if json_out:
        print(_json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
        return
    table = Table(title=f"rosmac deps — {root}")
    table.add_column("버킷")
    table.add_column("패키지")
    table.add_row("installed", ", ".join(report.installed) or "-")
    table.add_row("[yellow]missing[/]", ", ".join(report.missing) or "-")
    table.add_row("[red]unknown[/]", ", ".join(report.unknown) or "-")
    table.add_row("[red]unavailable[/]", ", ".join(report.unavailable) or "-")
    table.add_row("(ws 내부)", ", ".join(report.skipped_local) or "-")
    console.print(table)
    if report.missing:
        console.print(
            f"[yellow]→ rosmac deps {ws} --install[/] 또는:\n"
            f"  micromamba install -n {cfg.conda_env} -c conda-forge "
            f"-c {cfg.conda_channel} {' '.join(report.missing)}"
        )
    if report.unknown:
        console.print(
            "[red]unknown[/]: 매핑 확신 불가 — 시스템 의존성일 수 있음. "
            "conda-forge에서 이름을 찾아 수동 설치 후, 매핑을 알게 되면 "
            "deps.py SPECIAL_MAP에 기여해 주세요"
        )


@app.command()
def sim(
    name: str = typer.Argument(..., help="프리셋 이름, 또는 stop|status|list"),
    attach: bool = typer.Option(False, "--attach", help="tmux 세션에 붙어 로그 관찰"),
    no_viz: bool = typer.Option(False, "--no-viz", help="READY 후 Foxglove를 열지 않음"),
) -> None:
    """VM에서 시뮬 프리셋 기동 (tmux) → health 폴링 → READY 시 Foxglove 오픈."""
    import os

    from rosmac import doctor as doctor_mod
    from rosmac import sim as sim_mod

    cfg = load()

    if name == "list":
        table = Table(title="rosmac sim 프리셋")
        table.add_column("이름")
        table.add_column("설명")
        for n, desc in sorted(sim_mod.list_presets().items()):
            table.add_row(n, desc)
        console.print(table)
        return
    if name == "stop":
        console.print("✓ sim 세션 종료" if sim_mod.stop(cfg) else "- 실행 중인 sim 세션 없음")
        return
    if name == "status":
        console.print(sim_mod.status(cfg))
        return
    if attach:
        os.execvp("limactl", ["limactl", "shell", cfg.vm.name, "--",
                              "tmux", "attach", "-t", sim_mod.SESSION])

    try:
        preset = sim_mod.load_preset(name)
    except KeyError as e:
        console.print(f"[red]{e.args[0]}[/]")
        raise typer.Exit(1) from None

    # 사전 점검 (C2 VM, C5 포트, C6 맥 브리지, C7 VM 브리지 — C8은 느려서 제외)
    pre = [c for c in doctor_mod.CHECKS
           if c.name.split()[0] in ("C2", "C5", "C6", "C7")]
    failed = [r for r in (c.run(cfg) for c in pre) if r.status == "FAIL"]
    if failed:
        for r in failed:
            console.print(f"[red]{r.name}: {r.detail}[/] → {r.remedy}")
        raise typer.Exit(1)

    installed = sim_mod.ensure_apt(cfg, preset.vm_apt, progress=lambda m: console.print(f"  {m}"))
    if installed:
        console.print(f"✓ VM 패키지 설치: {', '.join(installed)}")
    try:
        sim_mod.start(cfg, preset)
    except RuntimeError as e:
        console.print(f"[yellow]{e}[/]")
        raise typer.Exit(1) from None
    console.print(f"✓ tmux 세션 '{sim_mod.SESSION}' 기동 — 로그: rosmac sim --attach")
    with console.status("[cyan]health topics 대기 중…[/]"):
        try:
            sim_mod.wait_healthy(cfg, preset, progress=lambda m: console.print(f"  {m}"))
        except RuntimeError as e:
            from rich.markup import escape

            # 로그 tail에 [ ... ] 가 흔해 rich 마크업으로 오파싱됨 — escape 필수
            console.print(f"[red]{escape(str(e))}[/]")
            sim_mod.stop(cfg)
            raise typer.Exit(1) from None
    console.print("[green bold]READY[/]")
    if not no_viz:
        _start_viz(cfg)


@app.command()
def status() -> None:
    """VM/브리지/포트/conda env 상태 테이블."""
    cfg = load()
    table = Table(title="rosmac status")
    table.add_column("항목")
    table.add_column("상태")

    vm_state = lima.state(cfg.vm.name)
    table.add_row("VM", vm_state.value)

    if vm_state is lima.VmState.RUNNING:
        vm_bridge = lima.shell(cfg.vm.name, "systemctl is-active zenoh-bridge || true").strip()
    else:
        vm_bridge = "-"
    table.add_row("VM 브리지(systemd)", vm_bridge)

    table.add_row("맥 브리지", "running" if bridge.is_running() else "stopped")

    import socket

    try:
        with socket.create_connection(("127.0.0.1", cfg.bridge.port), timeout=2):
            port_ok = "open"
    except OSError:
        port_ok = "closed"
    table.add_row(f"포트 {cfg.bridge.port}", port_ok)

    table.add_row("conda env", cfg.conda_env if conda.env_exists(cfg.conda_env) else "없음")
    console.print(table)

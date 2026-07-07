import typer
from rich.console import Console

import rosmac

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

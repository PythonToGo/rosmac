import tomllib
from pathlib import Path

from typer.testing import CliRunner

import rosmac
from rosmac.cli import app

runner = CliRunner()

PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"


def test_version_outputs_package_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert rosmac.__version__ in result.output


def test_version_flag() -> None:
    """P5.1 AC: `rosmac --version`."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert rosmac.__version__ in result.output


def test_version_single_source() -> None:
    """pyproject가 버전을 하드코딩하지 않고 __init__.py를 단일 소스로 쓴다 (P5.1)."""
    data = tomllib.loads(PYPROJECT.read_text())
    assert "version" not in data["project"], "pyproject에 버전 하드코딩 금지"
    assert "version" in data["project"]["dynamic"]
    assert data["tool"]["hatch"]["version"]["path"] == "src/rosmac/__init__.py"


def test_version_is_semver() -> None:
    """D12: SemVer — MAJOR.MINOR.PATCH 형식."""
    parts = rosmac.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)

from typer.testing import CliRunner

import rosmac
from rosmac.cli import app

runner = CliRunner()


def test_version_outputs_package_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert rosmac.__version__ in result.output

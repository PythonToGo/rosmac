"""bridge.build_args — robot 엔드포인트/필터 구성 (D15, E.15 R2)."""

from rosmac import bridge, config


def test_default_single_endpoint() -> None:
    cfg = config.Config()
    args = bridge.build_args(cfg)
    assert args[1:] == ["-e", "tcp/127.0.0.1:7447"]
    assert "--allow" not in args and "--deny" not in args


def test_robot_adds_endpoint_and_filters() -> None:
    cfg = config.Config(
        robot=config.RobotConfig(host="10.0.0.7", port=7457, allow="/cmd_vel|/odom")
    )
    args = bridge.build_args(cfg)
    assert args.count("-e") == 2
    assert "tcp/10.0.0.7:7457" in args
    assert args[args.index("--allow") + 1] == "/cmd_vel|/odom"


def test_robot_endpoint_string() -> None:
    cfg = config.Config(robot=config.RobotConfig(host="robot.local"))
    assert bridge.robot_endpoint(cfg) == "tcp/robot.local:7447"

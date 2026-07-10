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


# ── E.7 바이너리 버전 보장 ────────────────────────────────────────────────


def test_parse_bridge_version() -> None:
    out = (
        "INFO main zenoh_bridge_ros2dds: zenoh-bridge-ros2dds v1.9.0\nzenoh-bridge-ros2dds v1.9.0\n"
    )
    assert bridge.parse_bridge_version(out) == "1.9.0"
    assert bridge.parse_bridge_version("garbage") is None


def test_ensure_binary_skips_when_version_matches(monkeypatch) -> None:
    cfg = config.Config()
    monkeypatch.setattr(bridge, "installed_version", lambda: cfg.bridge.version)
    monkeypatch.setattr(
        bridge, "_fetch", lambda c: (_ for _ in ()).throw(AssertionError("no fetch"))
    )
    assert bridge.ensure_binary(cfg) is False


def test_ensure_binary_refetches_on_mismatch_or_missing(monkeypatch) -> None:
    cfg = config.Config()
    fetched = []
    monkeypatch.setattr(bridge, "_fetch", lambda c: fetched.append(c.bridge.version))
    monkeypatch.setattr(bridge, "installed_version", lambda: "1.8.0")  # 구버전 → 갱신
    assert bridge.ensure_binary(cfg) is True
    monkeypatch.setattr(bridge, "installed_version", lambda: None)  # 부재/판독불가 → 설치
    assert bridge.ensure_binary(cfg) is True
    assert fetched == [cfg.bridge.version] * 2


def test_fetch_download_has_timeout(monkeypatch, tmp_path) -> None:
    # E.7 ③: 유일한 네트워크 호출에 타임아웃이 걸려 있는지 (무한 대기 방지, 구조 리뷰 B6)
    seen = {}

    class _Abort(Exception):
        pass

    def fake_urlopen(url, timeout=None):
        seen["timeout"] = timeout
        raise _Abort

    monkeypatch.setattr(bridge.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(bridge, "BIN_PATH", tmp_path / "bin" / "zenoh-bridge-ros2dds")
    try:
        bridge._fetch(config.Config())
    except _Abort:
        pass
    assert seen["timeout"] == bridge._DOWNLOAD_TIMEOUT > 0

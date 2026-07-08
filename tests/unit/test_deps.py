"""P4.2 — rosmac deps 매퍼 유닛 테스트 (micromamba는 mock)."""

from pathlib import Path

from rosmac import deps
from rosmac.config import Config

FIXTURE_WS = Path(__file__).parent.parent / "fixtures" / "deps_ws"


def test_map_dep_rules() -> None:
    # ① 특수 매핑
    assert deps.map_dep("eigen") == "eigen"
    assert deps.map_dep("python3-numpy") == "numpy"  # 표가 ②보다 우선
    assert deps.map_dep("libboost-dev") == "boost-cpp"
    # ② python3- 접두
    assert deps.map_dep("python3-requests") == "requests"
    # ③ ROS 관례 이름
    assert deps.map_dep("moveit_msgs") == "ros-humble-moveit-msgs"
    assert deps.map_dep("rclpy", distro="jazzy") == "ros-jazzy-rclpy"
    # 확신 불가 → None
    assert deps.map_dep("libweird-system-dev") is None
    assert deps.map_dep("SomeCamelCase") is None


def test_scan_workspace_collects_and_separates_local() -> None:
    declared, local, broken = deps.scan_workspace(FIXTURE_WS / "src")
    assert local == {"alpha", "beta"}
    assert {"rclpy", "xacro", "beta", "eigen", "std_msgs", "ament_cmake"} <= declared
    assert broken == []


def test_scan_workspace_reports_broken_xml(tmp_path) -> None:
    pkg = tmp_path / "src" / "bad"
    pkg.mkdir(parents=True)
    (pkg / "package.xml").write_text("<package><name>bad")  # 고의로 깨진 XML
    _, _, broken = deps.scan_workspace(tmp_path / "src")
    assert len(broken) == 1 and broken[0].endswith("bad/package.xml")


def test_analyze_buckets(monkeypatch) -> None:
    cfg = Config()
    monkeypatch.setattr(
        deps, "installed_packages", lambda _cfg: {"ros-humble-rclpy", "eigen"}
    )
    # 채널 존재: fake만 없음
    monkeypatch.setattr(
        deps,
        "package_available",
        lambda _cfg, pkg: pkg != "ros-humble-totally-fake-ros-pkg-xyz",
    )
    r = deps.analyze(cfg, FIXTURE_WS)
    assert "ros-humble-rclpy" in r.installed and "eigen" in r.installed
    assert "ros-humble-xacro" in r.missing and "ros-humble-std-msgs" in r.missing
    assert r.unknown == ["libweird-system-dev"]
    assert r.unavailable == ["ros-humble-totally-fake-ros-pkg-xyz"]
    # ws 내부 패키지 beta는 어떤 버킷에도 없음
    flat = r.installed + r.missing + r.unknown + r.unavailable
    assert not any("beta" in x for x in flat)
    assert r.skipped_local == ["alpha", "beta"]

"""rosmac report 번들 — 수집 범위(~/.rosmac 한정)·로그 캡·tar 구조 (P5.3 ③)."""

import tarfile
from pathlib import Path

import pytest

from rosmac import doctor, report
from rosmac.config import Config

CFG = Config()


@pytest.fixture()
def fake_rosmac_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".rosmac"
    (d / "log").mkdir(parents=True)
    (d / "config.yaml").write_text("vm:\n  name: rosmac\n")
    (d / "log" / "bridge.log").write_text("bridge line\n" * 10)
    (d / "log" / "big.log").write_bytes(b"x" * (report.MAX_LOG_BYTES + 5000))
    return d


@pytest.fixture()
def quiet_externals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor, "run_all", lambda cfg: [doctor.CheckResult("C1 test", "PASS", "ok")]
    )
    monkeypatch.setattr(report.doctor_mod, "run_all", doctor.run_all, raising=False)
    monkeypatch.setattr(report, "_cmd", lambda cmd: "vX.Y")
    monkeypatch.setattr(report, "_vm_units", lambda cfg: "VM not running\n")


def test_collect_contents_and_log_cap(
    fake_rosmac_dir: Path, quiet_externals: None, tmp_path: Path
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    names = report.collect(CFG, work, rosmac_dir=fake_rosmac_dir)
    assert {"doctor.json", "versions.txt", "config.yaml", "vm-units.txt"} <= set(names)
    assert "log/bridge.log" in names and "log/big.log" in names
    # 로그 캡: 큰 파일은 마지막 256KB만
    assert (work / "log" / "big.log").stat().st_size == report.MAX_LOG_BYTES
    assert "rosmac:" in (work / "versions.txt").read_text()
    assert '"C1 test"' in (work / "doctor.json").read_text()


def test_bundle_members_all_relative(
    fake_rosmac_dir: Path,
    quiet_externals: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC: 홈 밖 파일 없음 — tar 멤버가 전부 번들 루트 아래 상대 경로."""
    monkeypatch.setattr(report, "CONFIG_PATH", fake_rosmac_dir / "config.yaml")
    out, names = report.create_bundle(CFG, out_dir=tmp_path)
    assert out.exists() and out.name.startswith("rosmac-report-")
    with tarfile.open(out) as tar:
        members = tar.getnames()
    root = out.name.removesuffix(".tar.gz")
    assert all(m == root or m.startswith(f"{root}/") for m in members)
    assert not any(m.startswith("/") or ".." in m for m in members)
    assert f"{root}/doctor.json" in members and f"{root}/log/bridge.log" in members


# ── 로봇 호스트 마스킹 (E.15-R4: 번들에 로봇 주소 평문 금지) ─────────────

ROBOT_CFG = Config.model_validate({"robot": {"host": "10.0.0.5"}})


def test_mask_host() -> None:
    assert report.mask_host("connect tcp/10.0.0.5:7447 ok", "10.0.0.5") == (
        f"connect tcp/{report._HOST_MASK}:7447 ok"
    )
    assert report.mask_host("nothing here", "10.0.0.5") == "nothing here"
    assert report.mask_host("tcp/10.0.0.5:7447", None) == "tcp/10.0.0.5:7447"  # 미설정 무변경


def test_version_matrix_masks_robot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(report, "_cmd", lambda cmd: "vX.Y")
    out = report.version_matrix(ROBOT_CFG)
    assert "robot: configured" in out and "10.0.0.5" not in out
    assert "robot: not configured" in report.version_matrix(CFG)


def test_collect_bundle_has_no_robot_host(
    fake_rosmac_dir: Path, quiet_externals: None, tmp_path: Path
) -> None:
    (fake_rosmac_dir / "config.yaml").write_text("robot:\n  host: 10.0.0.5\n")
    (fake_rosmac_dir / "log" / "bridge.log").write_text("endpoints [tcp/10.0.0.5:7447]\n")
    work = tmp_path / "work2"
    work.mkdir()
    names = report.collect(ROBOT_CFG, work, rosmac_dir=fake_rosmac_dir)
    for n in names:
        assert "10.0.0.5" not in (work / n).read_text(), n

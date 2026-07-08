"""package.xml 의존성 → RoboStack conda 패키지 매핑 (P4.2).

rosdep이 conda/macOS에서 실질 동작하지 않는 갭을 메운다 — 선언된 의존성을
`ros-humble-*` / conda-forge 패키지명으로 매핑해 설치 여부·가용성을 판정한다.
(선언 안 된 런타임 의존은 못 잡는다 — 그건 doctor의 영역, KI-26 참고.)

파싱·매핑은 순수 함수로 분리 (유닛 테스트 대상). micromamba 호출은 conda 모듈 경유.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from pydantic import BaseModel

from rosmac import conda
from rosmac.config import Config

# package.xml(format 2/3)에서 수집하는 의존성 태그
DEP_TAGS = (
    "depend",
    "build_depend",
    "build_export_depend",
    "exec_depend",
    "test_depend",
    "buildtool_depend",
)

# 규칙 ①: rosdep/apt 키 → conda 패키지명 특수 매핑.
# 여기 없고 규칙 ②③으로도 확신 못 하는 이름은 unknown으로 보고한다
# (조용히 틀린 패키지를 설치하지 않는다 — phase4 설계).
SPECIAL_MAP = {
    "eigen": "eigen",
    "libboost-dev": "boost-cpp",
    "libopencv-dev": "libopencv",
    "pybind11-dev": "pybind11",
    "python3-numpy": "numpy",
    "python3-yaml": "pyyaml",
    "python3-pytest": "pytest",
    "python3-setuptools": "setuptools",
    "python3-opencv": "py-opencv",
}

# ROS 패키지명 관례: 소문자+숫자+언더스코어 (REP-144 계열)
_ROS_NAME = re.compile(r"^[a-z0-9_]+$")


class DepsReport(BaseModel):
    """4버킷 분류 결과. installed/missing/unavailable은 conda 패키지명,
    unknown은 package.xml의 원래 이름 그대로."""

    installed: list[str] = []
    missing: list[str] = []
    unknown: list[str] = []
    unavailable: list[str] = []
    skipped_local: list[str] = []  # ws 내부 패키지 (참고용)
    broken_xml: list[str] = []  # 파싱 실패한 package.xml (사용자가 고칠 대상)


def scan_workspace(src: Path) -> tuple[set[str], set[str], list[str]]:
    """src/ 이하 package.xml 재귀 수집.

    반환: (선언된 dep 이름 집합, ws 내부 패키지 이름 집합, 파싱 실패 파일 목록).
    """
    deps: set[str] = set()
    local: set[str] = set()
    broken: list[str] = []
    for pkgxml in sorted(src.rglob("package.xml")):
        try:
            root = ET.parse(pkgxml).getroot()
        except ET.ParseError:
            broken.append(str(pkgxml))
            continue
        name = root.findtext("name")
        if name:
            local.add(name.strip())
        for tag in DEP_TAGS:
            for el in root.iter(tag):
                if el.text and el.text.strip():
                    deps.add(el.text.strip())
    return deps, local, broken


def map_dep(name: str, distro: str = "humble") -> str | None:
    """dep 이름 → conda 패키지명. 확신 못 하면 None (unknown 버킷).

    ① 특수 매핑 표 → ② python3-<x> → <x> → ③ ROS 관례 이름 → ros-<distro>-<-화>.
    하이픈 포함(apt 스타일) 이름은 ①에 없으면 unknown — ros-humble-libfoo-dev처럼
    존재하지 않을 이름을 지어내지 않는다.
    """
    if name in SPECIAL_MAP:
        return SPECIAL_MAP[name]
    if name.startswith("python3-"):
        return name.removeprefix("python3-")
    if _ROS_NAME.match(name):
        return f"ros-{distro}-{name.replace('_', '-')}"
    return None


def installed_packages(cfg: Config) -> set[str]:
    """env에 설치된 패키지 이름 집합 (micromamba 1회 호출 — KI-15 배려)."""
    p = conda._check(["micromamba", "list", "-n", cfg.conda_env, "--json"], timeout=120)
    return {e["name"] for e in json.loads(p.stdout)}


def package_available(cfg: Config, pkg: str) -> bool:
    """채널(robostack-humble + conda-forge)에 패키지가 존재하는가 (repoquery 실측 형식)."""
    p = conda._check(
        [
            "micromamba",
            "repoquery",
            "search",
            "-c",
            "conda-forge",
            "-c",
            cfg.conda_channel,
            pkg,
            "--json",
        ],
        timeout=120,
    )
    return bool(json.loads(p.stdout).get("result", {}).get("pkgs"))


def analyze(cfg: Config, ws: Path) -> DepsReport:
    """워크스페이스의 선언 의존성을 4버킷으로 분류한다."""
    declared, local, broken = scan_workspace(ws / "src")
    report = DepsReport(skipped_local=sorted(local), broken_xml=broken)
    installed = installed_packages(cfg)
    for name in sorted(declared - local):
        mapped = map_dep(name, cfg.ros.distro)
        if mapped is None:
            report.unknown.append(name)
        elif mapped in installed:
            report.installed.append(mapped)
        elif package_available(cfg, mapped):
            report.missing.append(mapped)
        else:
            report.unavailable.append(mapped)
    return report


def install_missing(cfg: Config, pkgs: list[str], timeout: int = 1800) -> None:
    """missing 버킷을 한 번의 micromamba install로 설치한다."""
    if not pkgs:
        return
    conda._check(
        [
            "micromamba",
            "install",
            "-y",
            "-n",
            cfg.conda_env,
            "-c",
            "conda-forge",
            "-c",
            cfg.conda_channel,
            *pkgs,
        ],
        timeout=timeout,
    )

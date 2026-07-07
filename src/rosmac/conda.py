"""micromamba 래퍼. 외부 호출은 _run 하나를 거친다 (테스트 mock 지점).

주의(KI-15): `micromamba run`을 동시에 여러 개 띄우면 ~/.cache/mamba/proc 락 경합 —
rosmac은 순차 호출만 한다.
"""

import json
import os
import subprocess
from pathlib import Path

from rosmac.config import Config

# Phase 0.1에서 검증된 패키지 목록 + D9의 rmw 핀
ENV_PACKAGES = [
    "ros-humble-desktop",
    "ros-humble-rmw-cyclonedds-cpp",
    "ros-humble-xacro",  # desktop 메타패키지에 없음 — launch의 FindExecutable('xacro') 실패 (KI-26)
    "compilers",
    "cmake<4",  # cmake 4는 rosidl의 FindPythonInterp 제거로 메시지 패키지 빌드 불가 (KI-25)
    "pkg-config",
    "make",
    "ninja",
    "colcon-common-extensions",
    "rosdep",
]


def _env(_environ: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(_environ if _environ is not None else os.environ)
    env.setdefault("MAMBA_ROOT_PREFIX", str(Path.home() / "micromamba"))
    return env


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=_env())


def _check(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    p = _run(cmd, timeout)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed (exit {p.returncode}): {p.stderr.strip()}")
    return p


def env_exists(name: str) -> bool:
    p = _check(["micromamba", "env", "list", "--json"])
    envs = json.loads(p.stdout).get("envs", [])
    return any(Path(e).name == name for e in envs)


def create_env(cfg: Config, timeout: int = 3600) -> None:
    """RoboStack env 생성 (Phase 0.1 검증 절차). 이미 있으면 호출하지 말 것."""
    _check(
        [
            "micromamba",
            "create",
            "-y",
            "-n",
            cfg.conda_env,
            "-c",
            "conda-forge",
            "-c",
            cfg.conda_channel,
            *ENV_PACKAGES,
        ],
        timeout=timeout,
    )


def run_in_env(cfg: Config, cmd: str, timeout: int = 60) -> str:
    """env 안에서 명령 실행 (ROS 환경변수 주입 포함), stdout 반환."""
    from rosmac.assets import ensure_mac_cyclonedds

    p = _check(
        [
            "micromamba",
            "run",
            "-n",
            cfg.conda_env,
            "env",
            "ROS_LOCALHOST_ONLY=1",
            f"ROS_DOMAIN_ID={cfg.ros.domain_id}",
            f"RMW_IMPLEMENTATION={cfg.ros.rmw}",
            f"ROS_DISTRO={cfg.ros.distro}",
            f"CYCLONEDDS_URI={ensure_mac_cyclonedds()}",
            "bash",
            "-c",
            cmd,
        ],
        timeout=timeout,
    )
    return p.stdout

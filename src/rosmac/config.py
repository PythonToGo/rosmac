"""~/.rosmac/config.yaml 로드/생성/검증.

모든 서브커맨드는 이 모듈이 반환하는 Config만 읽는다 (하드코딩 금지 — PLAN.md 6절).
핀 값(버전/sha256/RMW/채널)은 Phase 0 실측 결과다: docs/plan/phase0-results.md.
"""

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError, field_validator

from rosmac.errors import UsageError

CONFIG_PATH = Path.home() / ".rosmac" / "config.yaml"

# --- Phase 0에서 핀한 값 (D7, D9, P0.3) ---
BRIDGE_VERSION = "1.9.0"
BRIDGE_SHA256_DARWIN = "997415721cfbb74b209b9968e7a7e4f6bed94e6afa4559ddb02ee1b2edccc899"
BRIDGE_SHA256_LINUX = "e3eb1fd4459e4b877653419b1c25eaf92418d70fe53ee767eca005f1a19443dc"
PINNED_RMW = "rmw_cyclonedds_cpp"  # D9: fastrtps는 브리지 경유 서비스가 깨짐 (KI-16)
PINNED_CHANNEL = "robostack-humble"

# E.7 업그레이드 경로: 핀 필드는 config.yaml에 **저장하지 않는다** — 파일에 남으면
# pip 업그레이드 후에도 구버전이 동결된다(E.7 배경 실측). 로드 시에도 "역대 기본값"과
# 같은 값은 버려서 코드 기본값을 따르게 한다(과거에 동결된 파일의 마이그레이션).
# 사용자가 명시한 커스텀 핀(역대 기본값이 아닌 값)만 살아남는다.
# ⚠️ 릴리스 절차: 핀을 올릴 때 **이전 값을 해당 집합에 남겨둘 것** (지우면 마이그레이션 깨짐).
_PIN_HISTORY: dict[tuple[str, ...], set[str]] = {
    ("bridge", "version"): {BRIDGE_VERSION},
    ("bridge", "sha256_darwin"): {BRIDGE_SHA256_DARWIN},
    ("bridge", "sha256_linux"): {BRIDGE_SHA256_LINUX},
    ("ros", "rmw"): {PINNED_RMW},
    ("conda_channel",): {PINNED_CHANNEL},
}


def _strip_pins(raw: dict) -> dict:
    """raw dict에서 역대 기본값과 일치하는 핀 키를 제거한다 (제자리 수정 후 반환)."""
    for path, known in _PIN_HISTORY.items():
        node: object = raw
        for key in path[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict) and node.get(path[-1]) in known:
            del node[path[-1]]
    return raw


class VmConfig(BaseModel):
    name: str = "rosmac"
    cpus: int = 4
    memory: str = "8GiB"
    disk: str = "30GiB"


class BridgeConfig(BaseModel):
    port: int = 7447
    version: str = BRIDGE_VERSION
    sha256_darwin: str = BRIDGE_SHA256_DARWIN
    sha256_linux: str = BRIDGE_SHA256_LINUX


class RobotConfig(BaseModel):
    # D15 (E.15): 실로봇 연결 — host가 None이면 전 기능 무효 (기존 사용자 무영향).
    # allow/deny는 zenoh 브리지 전역 토픽 필터라 VM 경로에도 적용됨에 유의.
    host: str | None = None
    port: int = 7447
    allow: str | None = None
    deny: str | None = None

    @field_validator("host")
    @classmethod
    def _host_shape(cls, v: str | None) -> str | None:
        # zenoh 엔드포인트 문자열에 그대로 들어가므로 hostname/IP 문자만 허용
        if v is not None and not re.fullmatch(r"[A-Za-z0-9._-]+", v):
            raise ValueError(f"robot.host must be a hostname or IP address, got: {v!r}")
        return v

    @field_validator("port")
    @classmethod
    def _port_range(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError(f"robot.port must be 1-65535, got: {v}")
        return v


class RosConfig(BaseModel):
    distro: str = "humble"
    domain_id: int = 0
    rmw: str = PINNED_RMW


class BuildConfig(BaseModel):
    # KI-25 우회 플래그를 담은 colcon 기본값 주입 (COLCON_DEFAULTS_FILE).
    # false면 주입하지 않는다 — 자기 defaults.yaml을 쓰는 사용자용 이스케이프 해치.
    colcon_defaults: bool = True


class Config(BaseModel):
    vm: VmConfig = VmConfig()
    bridge: BridgeConfig = BridgeConfig()
    robot: RobotConfig = RobotConfig()
    ros: RosConfig = RosConfig()
    build: BuildConfig = BuildConfig()
    conda_env: str = "ros_env"
    conda_channel: str = PINNED_CHANNEL
    foxglove_port: int = 8765


class ConfigError(UsageError):
    """config.yaml이 깨졌거나 스키마에 안 맞을 때 (exit 2). 메시지에 경로와 원인을 담는다."""


def load(path: Path = CONFIG_PATH) -> Config:
    """config를 로드한다. 파일이 없으면 기본값으로 생성한 뒤 로드한다."""
    if not path.exists():
        cfg = Config()
        save(cfg, path)
        return cfg
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{path} parse failed (YAML syntax error): {e}") from e
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} top level is not a mapping (got: {type(raw).__name__})")
    try:
        return Config.model_validate(_strip_pins(raw))
    except ValidationError as e:
        raise ConfigError(f"{path} schema validation failed:\n{e}") from e


def save(cfg: Config, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _strip_pins(cfg.model_dump())  # E.7: 기본값 핀은 파일에 동결하지 않는다
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

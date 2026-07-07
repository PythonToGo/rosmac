"""~/.rosmac/config.yaml 로드/생성/검증.

모든 서브커맨드는 이 모듈이 반환하는 Config만 읽는다 (하드코딩 금지 — PLAN.md 6절).
핀 값(버전/sha256/RMW/채널)은 Phase 0 실측 결과다: docs/plan/phase0-results.md.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

CONFIG_PATH = Path.home() / ".rosmac" / "config.yaml"

# --- Phase 0에서 핀한 값 (D7, D9, P0.3) ---
BRIDGE_VERSION = "1.9.0"
BRIDGE_SHA256_DARWIN = "997415721cfbb74b209b9968e7a7e4f6bed94e6afa4559ddb02ee1b2edccc899"
BRIDGE_SHA256_LINUX = "e3eb1fd4459e4b877653419b1c25eaf92418d70fe53ee767eca005f1a19443dc"
PINNED_RMW = "rmw_cyclonedds_cpp"  # D9: fastrtps는 브리지 경유 서비스가 깨짐 (KI-16)
PINNED_CHANNEL = "robostack-humble"


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


class RosConfig(BaseModel):
    distro: str = "humble"
    domain_id: int = 0
    rmw: str = PINNED_RMW


class Config(BaseModel):
    vm: VmConfig = VmConfig()
    bridge: BridgeConfig = BridgeConfig()
    ros: RosConfig = RosConfig()
    conda_env: str = "ros_env"
    conda_channel: str = PINNED_CHANNEL
    foxglove_port: int = 8765


class ConfigError(RuntimeError):
    """config.yaml이 깨졌거나 스키마에 안 맞을 때. 메시지에 경로와 원인을 담는다."""


def load(path: Path = CONFIG_PATH) -> Config:
    """config를 로드한다. 파일이 없으면 기본값으로 생성한 뒤 로드한다."""
    if not path.exists():
        cfg = Config()
        save(cfg, path)
        return cfg
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{path} 파싱 실패 (YAML 문법 오류): {e}") from e
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} 최상위가 매핑이 아님 (현재: {type(raw).__name__})")
    try:
        return Config.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"{path} 스키마 검증 실패:\n{e}") from e


def save(cfg: Config, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False, allow_unicode=True))

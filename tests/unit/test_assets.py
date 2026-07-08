import yaml

from rosmac import assets
from rosmac.config import Config


def test_render_lima_yaml_is_valid_yaml_with_config_values() -> None:
    cfg = Config()
    text = assets.render_lima_yaml(cfg)
    doc = yaml.safe_load(text)
    assert doc["cpus"] == 4
    assert doc["memory"] == "8GiB"
    assert doc["disk"] == "30GiB"
    ports = {f["guestPort"] for f in doc["portForwards"] if "guestPort" in f}
    assert ports == {7447, 8765}
    # KI-27: UDP 자동 포워딩 차단 규칙 2개 (일반 + guestIP 0.0.0.0)가 최상단에 있어야 함
    udp_ignores = [f for f in doc["portForwards"] if f.get("proto") == "udp" and f.get("ignore")]
    assert len(udp_ignores) == 2
    assert doc["portForwards"][0] in udp_ignores  # TCP 포워드보다 먼저 평가돼야 함
    assert len(doc["provision"]) == 3  # ros / zenoh-bridge / foxglove-bridge


def test_render_substitutes_pins_and_keeps_shell_vars() -> None:
    cfg = Config()
    text = assets.render_lima_yaml(cfg)
    # 핀 값이 주입됨
    assert 'VER="1.9.0"' in text
    assert cfg.bridge.sha256_linux in text
    assert "ROS_DOMAIN_ID=0" in text
    # 셸 변수/서브셸은 건드리지 않음 (델리미터 @ 덕분)
    assert "$(dpkg --print-architecture)" in text
    assert "${VER}" in text
    # 미치환 @플레이스홀더가 남아 있으면 안 됨
    assert "@bridge_version" not in text
    assert "@provision" not in text


def test_render_respects_custom_config() -> None:
    cfg = Config.model_validate({"vm": {"cpus": 8}, "bridge": {"port": 7448}})
    doc = yaml.safe_load(assets.render_lima_yaml(cfg))
    assert doc["cpus"] == 8
    assert 7448 in {f["guestPort"] for f in doc["portForwards"] if "guestPort" in f}

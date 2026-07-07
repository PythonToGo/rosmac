"""자산(템플릿/스크립트) 로드와 Lima YAML 렌더링.

jinja2를 쓰지 않는다 — string.Template에 델리미터 '@'를 써서 셸 스크립트의
`$VAR`/`$(...)`/`${...}`와 충돌을 피한다 (phase1 부록 C-3).
"""

from importlib import resources
from pathlib import Path
from string import Template

from rosmac.config import Config

RENDERED_LIMA_PATH = Path.home() / ".rosmac" / "lima" / "rosmac.yaml"


class _AtTemplate(Template):
    delimiter = "@"


def _read_asset(relpath: str) -> str:
    return (resources.files("rosmac") / "assets" / relpath).read_text()


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())


def render_lima_yaml(cfg: Config) -> str:
    """config를 주입한 Lima YAML 전문을 반환한다 (파일로 쓰진 않음)."""
    subs = {
        "cpus": str(cfg.vm.cpus),
        "memory": cfg.vm.memory,
        "disk": cfg.vm.disk,
        "bridge_port": str(cfg.bridge.port),
        "foxglove_port": str(cfg.foxglove_port),
        "bridge_version": cfg.bridge.version,
        "bridge_sha256_linux": cfg.bridge.sha256_linux,
        "domain_id": str(cfg.ros.domain_id),
        "distro": cfg.ros.distro,
        "rmw": cfg.ros.rmw,
    }
    provision_ros = _AtTemplate(_read_asset("provision/10-ros2-humble.sh")).substitute(subs)
    provision_bridge = _AtTemplate(_read_asset("provision/20-bridge.sh")).substitute(subs)
    provision_foxglove = _AtTemplate(_read_asset("provision/30-foxglove.sh")).substitute(subs)
    subs["provision_ros"] = _indent(provision_ros, 6)
    subs["provision_bridge"] = _indent(provision_bridge, 6)
    subs["provision_foxglove"] = _indent(provision_foxglove, 6)
    return _AtTemplate(_read_asset("lima/rosmac.yaml.tmpl")).substitute(subs)


def write_lima_yaml(cfg: Config, path: Path = RENDERED_LIMA_PATH) -> Path:
    """렌더링 결과를 ~/.rosmac/lima/rosmac.yaml에 쓰고 경로를 반환한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_lima_yaml(cfg))
    return path

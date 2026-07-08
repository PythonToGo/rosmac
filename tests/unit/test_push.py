"""P4.4 — rosmac push 안전장치 유닛 테스트."""

import pytest

from rosmac import lima


def test_push_tree_rejects_dest_outside_rosmac_ws() -> None:
    # rm -rf 대상은 ~/rosmac-ws/ 프리픽스만 허용 (D14 안전장치)
    with pytest.raises(ValueError):
        lima.push_tree("vm", "/tmp/src", "~/other-dir/src")
    with pytest.raises(ValueError):
        lima.push_tree("vm", "/tmp/src", "/etc")

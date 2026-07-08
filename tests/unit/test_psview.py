"""P4.3 — rosmac ps 순수 판정 로직 유닛 테스트."""

from rosmac import psview

PS_SAMPLE = """\
  100 /Users/u/.rosmac/bin/zenoh-bridge-ros2dds -e tcp/127.0.0.1:7447
  200 /envs/ros_env/bin/python -c from ros2cli.daemon.daemonize import main; main() --name ros2-daemon --ros-domain-id 0
  300 /ws/install/pkg/lib/pkg/rcm_node --ros-args -r __node:=rcm_node
  400 /envs/ros_env/bin/python /envs/ros_env/bin/ros2 topic echo /joint_states --once
  500 vim notes.md
  600 /Users/u/.rosmac/bin/zenoh-bridge-ros2dds -e tcp/127.0.0.1:7447
  999 grep something
"""

# humble `ros2 topic info /tf --verbose` 축약 실측 형태
TOPIC_INFO_DUAL = """\
Type: tf2_msgs/msg/TFMessage

Publisher count: 2

Node name: robot_state_publisher
Node namespace: /
Topic type: tf2_msgs/msg/TFMessage
Endpoint type: PUBLISHER

Node name: zenoh_bridge_ros2dds
Node namespace: /
Topic type: tf2_msgs/msg/TFMessage
Endpoint type: PUBLISHER

Subscription count: 1

Node name: rviz2
Node namespace: /
"""


def test_parse_ps_lines_filters_and_excludes() -> None:
    procs = psview.parse_ps_lines(PS_SAMPLE, exclude_pids={400})
    pids = [p.pid for p in procs]
    assert pids == [100, 200, 300, 600]  # vim/grep 제외, 400은 자기 자신으로 제외


def test_parse_publisher_nodes_ignores_subscribers() -> None:
    pubs = psview.parse_publisher_nodes(TOPIC_INFO_DUAL)
    assert pubs == ["robot_state_publisher", "zenoh_bridge_ros2dds"]  # rviz2(구독자) 제외


def test_core_topic_warning_dual_source() -> None:
    # 2026-07-07 튕김 패턴: 로컬 + 브리지 유래 동시 발행
    warn = psview.core_topic_warning(["robot_state_publisher", "zenoh_bridge_ros2dds"])
    assert warn is not None and "브리지 유래" in warn
    # 단일 발행자는 경고 없음
    assert psview.core_topic_warning(["robot_state_publisher"]) is None
    # 로컬 2개도 확인 요청 경고
    assert psview.core_topic_warning(["a", "b"]) is not None


def test_find_orphan_bridges() -> None:
    procs = psview.parse_ps_lines(PS_SAMPLE, exclude_pids=set())
    orphans = psview.find_orphan_bridges(procs, pidfile_pid=100)
    assert [o.pid for o in orphans] == [600]
    # pidfile이 없으면(브리지 정상 종료 후 잔재) 둘 다 고아
    assert [o.pid for o in psview.find_orphan_bridges(procs, None)] == [100, 600]

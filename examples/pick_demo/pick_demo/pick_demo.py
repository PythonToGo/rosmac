"""pick_demo — 맥 네이티브 rclpy 노드가 zenoh 브리지 너머 VM의 MoveIt을 구동한다.

named target(ready → extended → ready)을 JointConstraint로 순회 (phase2 부록 A 방식).
관절값은 moveit_resources_panda_moveit_config의 panda.srdf group_state 실측값 (P2.3).
판정: 각 goal의 result error_code.val == 1 (moveit_msgs SUCCESS).
"""

import sys

import rclpy
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint
from rclpy.action import ActionClient
from rclpy.node import Node

# panda.srdf group_state 실측값 (P2.3, 2026-07-07)
POSES = {
    "ready": {
        "panda_joint1": 0.0, "panda_joint2": -0.785, "panda_joint3": 0.0,
        "panda_joint4": -2.356, "panda_joint5": 0.0, "panda_joint6": 1.571,
        "panda_joint7": 0.785,
    },
    "extended": {
        "panda_joint1": 0.0, "panda_joint2": 0.0, "panda_joint3": 0.0,
        "panda_joint4": 0.0, "panda_joint5": 0.0, "panda_joint6": 1.571,
        "panda_joint7": 0.785,
    },
}
SEQUENCE = ["ready", "extended", "ready"]
SUCCESS = 1  # moveit_msgs/MoveItErrorCodes.SUCCESS


class MoveClient(Node):
    def __init__(self) -> None:
        super().__init__("pick_demo")
        self.client = ActionClient(self, MoveGroup, "/move_action")

    def goal_for(self, joints: dict[str, float]) -> MoveGroup.Goal:
        g = MoveGroup.Goal()
        g.request.group_name = "panda_arm"  # panda.srdf 그룹명 (실측)
        g.request.allowed_planning_time = 5.0
        g.request.num_planning_attempts = 3
        c = Constraints()
        c.joint_constraints = [
            JointConstraint(
                joint_name=k, position=v,
                tolerance_above=0.01, tolerance_below=0.01, weight=1.0,
            )
            for k, v in joints.items()
        ]
        g.request.goal_constraints = [c]
        g.planning_options.plan_only = False  # 플래닝 + 실행
        return g

    def move_to(self, name: str) -> bool:
        self.get_logger().info(f"goal 전송: {name}")
        goal_future = self.client.send_goal_async(self.goal_for(POSES[name]))
        rclpy.spin_until_future_complete(self, goal_future, timeout_sec=30)
        handle = goal_future.result()
        if handle is None or not handle.accepted:
            self.get_logger().error(f"{name}: goal 거부/타임아웃")
            return False
        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=60)
        result = result_future.result()
        if result is None:
            self.get_logger().error(f"{name}: result 타임아웃")
            return False
        code = result.result.error_code.val
        ok = code == SUCCESS
        level = self.get_logger().info if ok else self.get_logger().error
        level(f"{name}: error_code={code} → {'SUCCEEDED' if ok else 'FAILED'}")
        return ok


def main() -> None:
    rclpy.init()
    node = MoveClient()
    if not node.client.wait_for_server(timeout_sec=20):
        print("move_action 서버 없음 — rosmac sim panda-moveit 실행 여부 확인", file=sys.stderr)
        raise SystemExit(2)
    results = [node.move_to(name) for name in SEQUENCE]
    node.destroy_node()
    rclpy.shutdown()
    if all(results):
        print(f"pick_demo: {len(results)}/{len(results)} SUCCEEDED")
        return
    raise SystemExit(1)


if __name__ == "__main__":
    main()

"""nav2-diffbot 프리셋 headless launch (E.17 N1/N2 실측 확정 구성).

Gazebo Fortress(diffbot + gpu_lidar, 벽 아레나) → ros_gz_bridge →
slam_toolbox(online async, mapping) → nav2_bringup(navigation, autostart).
맥에서 /navigate_to_pose 액션으로 목표 전송(브리지 스코핑 전제 — KI-30),
Foxglove로 map+scan+path 시각화.

N1 실측 확정:
- lidar frame_id=lidar_link(<ignition_frame_id>), 정적 tf base_link→lidar_link
- DiffDrive frame_id=odom child=base_link, odom 50Hz, tf는 /model/vehicle_blue/tf 브리지
- /clock 브리지 + 전 노드 use_sim_time
- nav2 기본 파라미터로 충분(base_link/odom/scan 기본값이 프레임 설계와 일치)
- 기동 타이밍: gz+bridge 먼저 → slam(+5s) → nav2(+10s) (run_spike.sh 순서)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

PRESET = os.path.expanduser("~/rosmac-presets/nav2-diffbot")
WORLD = os.path.join(PRESET, "nav2_world.sdf")
SLAM_PARAMS = os.path.join(PRESET, "slam_params.yaml")


def generate_launch_description():
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")
    pkg_slam = get_package_share_directory("slam_toolbox")
    pkg_nav2 = get_package_share_directory("nav2_bringup")

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": f"-s --headless-rendering -r {WORLD}"}.items(),
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        # 단방향(P2.4 실측) — cmd_vel만 ROS→GZ(]), 나머지 GZ→ROS([)
        arguments=[
            "/model/vehicle_blue/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
            "/model/vehicle_blue/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/model/vehicle_blue/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        ],
        remappings=[
            ("/model/vehicle_blue/cmd_vel", "/cmd_vel"),
            ("/model/vehicle_blue/odometry", "/odom"),
            ("/model/vehicle_blue/tf", "/tf"),
        ],
        parameters=[{"qos_overrides./model/vehicle_blue.subscriber.reliability": "reliable"}],
        output="screen",
    )

    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=[
            "--x",
            "0.648573",
            "--z",
            "0.675",
            "--frame-id",
            "base_link",
            "--child-frame-id",
            "lidar_link",
        ],
        parameters=[{"use_sim_time": True}],
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_slam, "launch", "online_async_launch.py")),
        launch_arguments={
            "use_sim_time": "true",
            "slam_params_file": SLAM_PARAMS,
        }.items(),
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_nav2, "launch", "navigation_launch.py")),
        launch_arguments={"use_sim_time": "true"}.items(),
    )

    return LaunchDescription(
        [
            gz_sim,
            bridge,
            static_tf,
            # 신뢰성 우선 stagger (S0 실측: 촘촘하면 nav2 lifecycle 활성화가 간헐 실패).
            # gz가 벽 아레나 월드 로드 + /clock·/scan 발행을 마칠 시간(~10s) 뒤 SLAM,
            # SLAM이 map→odom tf를 세운 뒤(~8s) Nav2 — run_spike.sh 검증 타이밍 + 여유.
            TimerAction(period=10.0, actions=[slam]),
            TimerAction(period=18.0, actions=[nav2]),
        ]
    )

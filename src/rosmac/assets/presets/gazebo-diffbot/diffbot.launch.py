"""gazebo-diffbot 프리셋용 headless launch.

ros_gz_sim_demos의 diff_drive.launch.py 기반, 실측으로 확정한 변경 (P2.4):
- rviz 제거, Gazebo Fortress 서버 전용(-s) + --headless-rendering (EGL)
- 동봉 월드 diffbot_camera.sdf 사용: diff_drive.sdf + sensors 시스템(ogre2) +
  vehicle_blue 전방 카메라 320x240@15Hz (기본 ogre 엔진은 X11 필요라 헤드리스 크래시)
- vehicle_blue를 /cmd_vel·/odom으로 리매핑, /camera 브리지 추가
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

WORLD = os.path.expanduser("~/rosmac-presets/gazebo-diffbot/diffbot_camera.sdf")


def generate_launch_description():
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": f"-s --headless-rendering -r {WORLD}"}.items(),
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        # 단방향 브리지 — @(양방향)를 쓰면 GZ→ROS 출력이 ROS→GZ로 되먹임됨 (P2.4 실측)
        arguments=[
            "/model/vehicle_blue/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
            "/model/vehicle_blue/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/camera@sensor_msgs/msg/Image[gz.msgs.Image",
        ],
        remappings=[
            ("/model/vehicle_blue/cmd_vel", "/cmd_vel"),
            ("/model/vehicle_blue/odometry", "/odom"),
        ],
        parameters=[
            {"qos_overrides./model/vehicle_blue.subscriber.reliability": "reliable"}
        ],
        output="screen",
    )

    return LaunchDescription([gz_sim, bridge])

#!/bin/bash
set -eux
# --- docs.ros.org Humble 공식 설치 절차 (Phase 0.2 검증본) ---
apt-get update && apt-get install -y locales curl gnupg lsb-release unzip
locale-gen en_US en_US.UTF-8
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
add-apt-repository -y universe
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  > /etc/apt/sources.list.d/ros2.list
# OSRF gazebo-stable 저장소 필수 — packages.ros.org의 libignition-sensors6(6.8.0)이
# desktop-full 의존성(>=6.8.1)을 못 채워 apt가 깨짐 (Phase 0 실측, KI-13)
curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
  -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
  > /etc/apt/sources.list.d/gazebo-stable.list
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ros-humble-desktop-full ros-dev-tools ros-humble-rmw-cyclonedds-cpp
echo "source /opt/ros/humble/setup.bash" >> /etc/skel/.bashrc
for f in /home/*/.bashrc; do echo "source /opt/ros/humble/setup.bash" >> "$f"; done

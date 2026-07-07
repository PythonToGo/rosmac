#!/bin/bash
set -eux
# foxglove_bridge — VM 쪽에서 실행 (phase2 2.1 설계: 고대역 센서가 zenoh를 우회해
# 8765 포트포워딩으로 직행, R4 회피). 기본 disabled — rosmac up --viz / sim에서 start.
DEBIAN_FRONTEND=noninteractive apt-get install -y ros-humble-foxglove-bridge tmux

cat > /etc/systemd/system/foxglove-bridge.service <<'UNIT'
[Unit]
Description=foxglove_bridge websocket (rosmac)
After=network-online.target

[Service]
# HOME 없으면 rcl_logging이 "Failed to get logging directory"로 죽음 (Phase 2 실측)
Environment=HOME=/root ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=@domain_id RMW_IMPLEMENTATION=@rmw
ExecStart=/bin/bash -c 'source /opt/ros/@distro/setup.bash && exec ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=@foxglove_port -p address:=0.0.0.0'
Restart=on-failure
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
# enable하지 않는다 — 기본 disabled, rosmac up --viz / rosmac sim에서만 start (2.1 설계)

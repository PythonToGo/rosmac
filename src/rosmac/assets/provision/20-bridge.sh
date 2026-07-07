#!/bin/bash
set -eux
# zenoh-bridge-ros2dds 설치 (버전 핀 @bridge_version, sha256 검증) + systemd 등록.
# T9(재연결)는 systemd Restart에 위임. 정상 종료는 SIGTERM (KI-17).
VER="@bridge_version"
SHA="@bridge_sha256_linux"
ZIP="/tmp/zenoh-bridge.zip"
curl -sSL -o "$ZIP" \
  "https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds/releases/download/${VER}/zenoh-plugin-ros2dds-${VER}-aarch64-unknown-linux-gnu-standalone.zip"
echo "${SHA}  ${ZIP}" | sha256sum -c -
unzip -o "$ZIP" zenoh-bridge-ros2dds -d /usr/local/bin
chmod +x /usr/local/bin/zenoh-bridge-ros2dds
rm -f "$ZIP"

cat > /etc/systemd/system/zenoh-bridge.service <<'UNIT'
[Unit]
Description=zenoh-bridge-ros2dds (rosmac)
After=network-online.target

[Service]
Environment=ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=@domain_id ROS_DISTRO=@distro
ExecStart=/usr/local/bin/zenoh-bridge-ros2dds -l tcp/0.0.0.0:@bridge_port
Restart=on-failure
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now zenoh-bridge.service

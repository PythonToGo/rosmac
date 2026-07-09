# Connecting a real robot

*(한국어: [robot-setup.ko.md](robot-setup.ko.md))*

rosmac talks to your robot through a single TCP link: a `zenoh-bridge-ros2dds`
listener on the robot, which your Mac's bridge connects out to. Nothing else is
installed on the robot — this page is a copy-paste guide, `rosmac` never
executes anything on your robot.

```
Mac (RoboStack) ── zenoh bridge ──┬── tcp ──> Lima VM (Ubuntu, sim/build)
                                  └── tcp ──> robot :7447  ← this guide
```

The Mac initiates the connection (star topology), so the robot never needs to
reach into your Mac. The VM and the robot can also see each other's topics —
routing is transitive through the Mac bridge.

## 1. Prerequisites (read first)

- **Ubuntu robot with ROS 2 Humble.** Humble is the only supported distro in
  v1 — mixing distros over the bridge is untested territory.
- **Robot nodes must use the CycloneDDS RMW.** With the default Fast DDS,
  topics appear to work but **every service call through the bridge times
  out** (measured). On the robot:

  ```bash
  sudo apt install ros-humble-rmw-cyclonedds-cpp
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp   # put in ~/.bashrc / your launch env
  ```

- **Same `ROS_DOMAIN_ID` everywhere**: your robot nodes, the systemd unit
  below, and `ros.domain_id` in `~/.rosmac/config.yaml` on the Mac. A mismatch
  fails *silently* — the link looks healthy but no topics flow.
- **`ROS_LOCALHOST_ONLY` must match your robot nodes.** The bridge discovers
  your nodes over local DDS; if your nodes run with `ROS_LOCALHOST_ONLY=1`
  but the bridge doesn't (or vice versa), they never see each other — again
  a *silent* failure (measured). The unit below leaves it unset (the common
  robot setup); section 2.1 has the copy-paste fix for localhost-only robots.
- **Port 7447/tcp open** from the Mac to the robot
  (e.g. `sudo ufw allow 7447/tcp` if you use ufw).
- **Trusted LAN only.** The link is plaintext TCP with no authentication.
  Do not expose port 7447 beyond your local network.

## 2. Install on the robot (copy-paste)

Run this on the robot. It downloads the pinned bridge binary (sha256-verified,
aarch64/x86_64 auto-detected) and registers it as a systemd service.

<!-- robot-install-begin -->
```bash
#!/bin/bash
set -euo pipefail

VER="1.9.0"
case "$(uname -m)" in
  aarch64) ARCH="aarch64"; SHA="e3eb1fd4459e4b877653419b1c25eaf92418d70fe53ee767eca005f1a19443dc" ;;
  x86_64)  ARCH="x86_64";  SHA="91aa0d569fffd57e7ebb1a591b97789891c543b1ff0a1658413ce6cbbba34a9e" ;;
  *) echo "unsupported arch: $(uname -m)"; exit 1 ;;
esac
ZIP="/tmp/zenoh-bridge.zip"
curl -sSL -o "$ZIP" \
  "https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds/releases/download/${VER}/zenoh-plugin-ros2dds-${VER}-${ARCH}-unknown-linux-gnu-standalone.zip"
echo "${SHA}  ${ZIP}" | sha256sum -c -
sudo unzip -o "$ZIP" zenoh-bridge-ros2dds -d /usr/local/bin
sudo chmod +x /usr/local/bin/zenoh-bridge-ros2dds
rm -f "$ZIP"

sudo tee /etc/systemd/system/zenoh-bridge-ros2dds.service > /dev/null <<'UNIT'
[Unit]
Description=zenoh-bridge-ros2dds (robot side, for rosmac)
After=network-online.target

[Service]
# ROS_DOMAIN_ID must match your robot nodes AND ros.domain_id on the Mac.
Environment=ROS_DOMAIN_ID=0 ROS_DISTRO=humble
ExecStart=/usr/local/bin/zenoh-bridge-ros2dds -l tcp/0.0.0.0:7447
Restart=on-failure
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now zenoh-bridge-ros2dds.service
```
<!-- robot-install-end -->

Verify on the robot:

```bash
systemctl is-active zenoh-bridge-ros2dds   # → active
ss -tln | grep 7447                        # → LISTEN 0.0.0.0:7447
journalctl -u zenoh-bridge-ros2dds --no-pager | grep Discovered   # → your nodes
```

If the last command shows none of your nodes, the bridge can't see them over
DDS — check `ROS_DOMAIN_ID` and `ROS_LOCALHOST_ONLY` (both fail silently).

### 2.1 If your robot nodes run with `ROS_LOCALHOST_ONLY=1`

The bridge must match, or it will never discover them. Copy-paste:

<!-- robot-localhost-begin -->
```bash
sudo mkdir -p /etc/systemd/system/zenoh-bridge-ros2dds.service.d
printf '[Service]\nEnvironment=ROS_LOCALHOST_ONLY=1\n' | \
  sudo tee /etc/systemd/system/zenoh-bridge-ros2dds.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart zenoh-bridge-ros2dds
```
<!-- robot-localhost-end -->

The Mac reconnects automatically after the restart — no action needed there.

## 3. Connect from the Mac

Edit `~/.rosmac/config.yaml` — add the robot's IP (or hostname):

```yaml
robot:
  host: 192.168.0.42   # your robot's address
  port: 7447
```

Then:

```bash
rosmac up
# ✓ robot endpoint reachable (tcp/192.168.0.42:7447)
```

If the Mac bridge was already running before you edited the config, `up`
prints a drift warning — follow it:

```bash
rosmac down --keep-vm && rosmac up
```

Check the link and receive a robot topic:

```bash
rosmac status      # Robot (tcp/192.168.0.42:7447) │ reachable
rosmac ps          # ── Robot link ── section: reachable ✓  in bridge args ✓
rosmac shell
ros2 topic list    # robot topics appear alongside VM topics
ros2 topic echo /your_robot_topic --once
```

To disconnect, set `host: null` (or remove the `robot:` block) and restart the
bridge the same way.

## 4. Operating notes

- **Robot off is fine.** `rosmac up` only warns (exit 0) when the robot is
  unreachable; the Mac bridge auto-connects the moment the robot's listener
  appears. Robot reboots and bridge restarts need no action on the Mac.
- **Restart services cleanly (SIGTERM), never `kill -9`.** An unclean kill of
  a robot-side ROS service server leaves a stale named route in the bridge
  that can block a replacement server until it re-declares (measured).
  `sudo systemctl restart zenoh-bridge-ros2dds` does the right thing.
- **`robot.allow` / `robot.deny` filters are global** to the Mac bridge — they
  also filter the Mac↔VM path, not just the robot link.
- **Bridge versions**: this guide pins 1.9.0. A 1.8.x bridge on the robot
  interoperates with the Mac's 1.9 (topics and services, measured), but keep
  the same minor version when you can.
- **Bandwidth/latency reference** (loopback surrogate, WiFi numbers pending):
  10 MB/s sustained at 10 Hz without drops, service RTT < 1 ms. Expect WiFi
  to be the bottleneck for camera/pointcloud topics — use `robot.deny` to
  keep heavy topics off the link if needed.

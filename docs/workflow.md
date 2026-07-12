# rosmac development workflow — write code on the Mac, drive the stack in the VM

[한국어 (Korean)](workflow.ko.md)

> This document shows how the "Mac-native dev loop" actually runs, using a worked example (pick_demo).
> Finish the Quickstart in the README first (`rosmac init && rosmac up`).

## 1. The two paths data flows through

```
┌─ macOS ────────────────────────────────────────────────────┐
│  ① dev loop: rosmac shell → colcon build → ros2 run …      │
│     (RoboStack conda env, rclpy nodes run on the Mac)      │
│                                                            │
│  [zenoh-bridge (Mac)] ←→ tcp:7447 ←→ [zenoh-bridge (VM)]   │
│     ↑ topics/services/actions transparently reach VM DDS   │
│                                                            │
│  Foxglove app ←── ws:8765 ──── [foxglove_bridge (VM)]      │
│     ↑ viz reads VM DDS directly, bypassing zenoh (high-bw) │
│  ┌─ Lima VM (Ubuntu 22.04 arm64) ───────────────────────┐  │
│  │ move_group / Gazebo / ros_gz_bridge / systemd bridges│  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

- **zenoh path** (7447): topics, services, and actions between rclpy/rclcpp
  nodes on the Mac and nodes in the VM.
- **foxglove path** (8765): visualization only. It looks at the VM-local DDS
  directly, so it is independent of the zenoh bridge's state, and high-bandwidth
  topics such as cameras flow without a bottleneck (design: phase2 2.1).

## 2. The dev loop (using pick_demo)

```bash
rosmac up                      # start the VM + bridges
rosmac sim panda-moveit        # bring up the MoveIt stack in the VM, wait until READY

rosmac deps .                  # before building: check package.xml deps (replaces rosdep on the Mac)
                               #   if anything is missing, install it in one go with --install
rosmac shell                   # enter a subshell with the ROS env injected — zero manual env setup
cd ~/workspace/rosmac/examples
colcon build                   # Mac-native build (RoboStack)
source install/setup.zsh
ros2 run pick_demo pick_demo   # runs on the Mac → VM MoveIt plans/executes
```

pick_demo cycles through named targets (ready→extended→ready) with a MoveGroup
action client. The goal crosses the zenoh bridge to the VM's `/move_action`,
and feedback/result come back. You can watch the arm move in the Foxglove 3D panel.

The debugger attaches like plain Python: inside `rosmac shell`, run
`python -m pdb $(which pick_demo)`, or point your IDE interpreter at
`~/micromamba/envs/ros_env/bin/python`.

### Mobile navigation (`rosmac sim nav2-diffbot`)

```bash
rosmac sim nav2-diffbot         # Gazebo diffbot + lidar + SLAM + Nav2, wait until READY
rosmac viz --layout nav2        # Foxglove: map + laser scan + planned path

rosmac shell                    # from the Mac:
# drive a lap with /cmd_vel to let SLAM build the map, then:
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 1.5, y: 1.0}, orientation: {w: 1.0}}}}"
```

The goal crosses the bridge to the VM's `/navigate_to_pose`; the robot plans and
drives, and `/map` · `/plan` · `/scan` stream back to the Mac for Foxglove. The
full Nav2 stack (155 services, 12 actions) works over the default bridge — no
scoping. `rosmac sim` resets the bridge session on start so the new stack gets
fresh routes; without that, routes left over from a prior stack silently break
Mac-side action discovery (KI-17). Sending goals from the Mac needs
`ros-humble-nav2-msgs` in the Mac env — `rosmac sim` installs it automatically
(the preset's `mac_env_pkgs`), so no manual step.

Limits of `rosmac deps`: it only sees dependencies **declared in package.xml**.
Executables the code uses without declaring them (launch's `FindExecutable`
etc., the KI-26 case) slip through — that class of problem belongs to the
pitfall table and doctor.

### Packages that won't build on the Mac → build in the VM (`rosmac push`)

Packages with **linux-only dependencies**, such as libfranka, fundamentally
cannot build on the Mac. The official escape hatch:

```bash
rosmac push ~/my_ws --build     # copy src/ to VM ~/rosmac-ws/my_ws/ + colcon build
rosmac shell --vm               # enter a VM shell
source ~/rosmac-ws/my_ws/install/setup.bash && ros2 run …
```

- It works by copying (D14), so after editing you need to re-push. A re-push
  **replaces the VM-side src wholesale**.
- For apt dependencies, the VM is stock Ubuntu, so rosdep works as-is:
  `rosdep install --from-paths src -y`
- Topics from nodes you run there cross the zenoh bridge and are visible on
  the Mac too.
- To see what is going on, always use `rosmac ps` — Mac+VM processes and key
  topic publishers on one screen.

### Recording and replaying (rosbag2) — measured 2026-07

rosbag2 works through the bridge in both directions:

```bash
# record on the Mac (bridged VM topics included)
rosmac shell
ros2 bag record -o mybag /chatter          # 20/20 msgs, no loss (measured)
ros2 bag play mybag                        # replay reaches VM subscribers too

# record inside the VM (heavy topics: prefer this — skips the bridge hop)
rosmac shell --vm -c "ros2 bag record -o /tmp/vmbag /chatter"

# retrieve a VM-side bag to the Mac (D16: no extra tool — lima has this built in)
limactl cp -r rosmac:/tmp/vmbag ~/vmbag
```

Two things to know: the **first** subscription to a new topic (including
`bag record`) takes a few seconds while the bridge creates the route — don't
cut recordings that short. And for high-rate/large topics, record **inside
the VM** and copy the bag out afterwards; that measures the true publish rate
instead of the bridge link.

## 3. Common pitfalls (when stuck, run `rosmac doctor` first)

| Symptom | Cause | Tool |
|---|---|---|
| Topics not visible / only sometimes | missing env vars (ROS_LOCALHOST_ONLY etc.) — ros2 was run from a bare shell | doctor C4, use `rosmac shell` (KI-6) |
| Same message received twice | leftovers from a bridge that exited uncleanly | `rosmac down --keep-vm && rosmac up` (KI-17) |
| Only services/actions unresponsive | RMW leaked to fastrtps | doctor C4 — must be cyclonedds (KI-16, D9) |
| Node dies with a "participant index" error | CycloneDDS 10-participant limit | check the CYCLONEDDS_URI that rosmac injects (KI-23) |
| `ros2 run` can't find the executable | setuptools installed it into bin/ | add setup.cfg to the package (KI-22) |
| ros2 not found in VM commands | bash -lc does not source .bashrc | use `rosmac shell --vm -c` (KI-19) |
| Build fails with `Could NOT find Python` | outdated cmake_minimum_required(3.5) + CMP0094 | auto-worked-around inside `rosmac shell` (P4.1 injection). Outside it, `--cmake-args -DCMAKE_POLICY_DEFAULT_CMP0094=NEW` (KI-25) |
| launch fails with `TextSubstitution object ... not found on the PATH` | the FindExecutable target (usually xacro) is missing from the env | `micromamba install -n ros_env ... ros-humble-xacro` (KI-26) |
| `ros2 topic echo/list` hangs forever | ros2 daemon hang | `rosmac ps` detects and prescribes it. `ros2 daemon stop && ros2 daemon start` (inside rosmac shell) |
| Mac↔VM topics suddenly stop flowing | lima UDP forwarding hijacking DDS ports (KI-27) or bridge discovery stall (KI-28) | check publishers with `rosmac ps` → `lsof -nP -iUDP \| grep limactl` (KI-27) → restart the bridges |

Full pitfall DB: [docs/plan/known-issues.md](plan/known-issues.md)

## 4. Connecting a real robot (beta)

The same single-TCP model extends to a robot on your LAN: one
`zenoh-bridge-ros2dds` listener on the robot, one extra endpoint on the Mac
bridge. No new commands — configure and `rosmac up`:

```yaml
# ~/.rosmac/config.yaml
robot:
  host: 192.168.0.42   # robot's IP; null (default) disables the feature
  port: 7447
```

`rosmac status` / `ps` show the link, `doctor` C16 diagnoses it. The robot
being off is fine — the Mac reconnects automatically when it appears.
Full setup (copy-paste install script, prerequisites, silent-failure
checklist): [robot-setup.md](robot-setup.md). Trusted LAN only — the link is
plaintext TCP. Status: **beta** — verified against a surrogate robot;
real-hardware/WiFi validation pending (E.15 R5).

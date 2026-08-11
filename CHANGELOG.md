# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versioning follows [SemVer](https://semver.org/) (D12).
**While on 0.y.z, minor versions may contain breaking changes.**

[한국어 (Korean)](CHANGELOG.ko.md)

## [0.1.0] - Unreleased

First public release candidate — retroactive summary of Phases 0–4.

### Added
- Core CLI: `init` (conda env, bridge, and VM provisioning; idempotent) /
  `up`·`down`·`status` / `doctor` (C1–C11 diagnostics with prescriptions, `--json`) /
  `shell` (ROS env injection, `--vm`, `-c`) / `version` (Phase 1)
- Simulation: `sim panda-moveit` and `sim gazebo-diffbot` presets (tmux launch +
  health verdict), `viz` (foxglove_bridge + app deep link) (Phase 2)
- External workspace support: `deps` (package.xml → RoboStack install, replaces
  rosdep) / `ps` (observes Mac + VM processes and topic publishers) / `push`
  (transfer to the VM, with `--build`) / automatic colcon build defaults
  (works around legacy CMake pitfalls) (Phase 4)
- Architecture: Mac-native development (RoboStack) ↔ zenoh bridge (TCP 7447) ↔
  Lima VM Ubuntu 22.04 arm64 (MoveIt, Gazebo) ↔ Foxglove (ws 8765),
  rmw_cyclonedds_cpp pinned on both sides (D9)
- Pitfall database: 30 known issues from field measurement
  (`docs/plan/known-issues.md`)
- Diagnostics & reporting: `doctor --fix` (auto-repairs safe items), `report`
  (diagnostic bundle tar.gz; never collects outside `~/.rosmac`) (Phase 5)
- **Real-robot connection (beta)**: `robot:` config section — the Mac bridge
  adds a TCP endpoint to the robot-side zenoh bridge (D15, no new commands).
  Reachability and drift warnings on `up`, robot link display in `status`/`ps`,
  `doctor` C16 diagnostic, robot-host masking in `report`, setup guide
  `docs/robot-setup.md`. Verified against a surrogate robot (second VM) —
  labeled "beta (surrogate-verified)" until validated on real hardware/WiFi
  (E.15 R0–R4, R6)
- Bridge capability matrix: topics/services/actions/parameters/rosbag measured
  and documented in the README — parameters are partially supported (raw
  services only; the `ros2 param` CLI does not work), VM bag retrieval via
  `limactl cp` (D16), three structural limitations stated explicitly (E.14)
- Upgrade path: version/sha pins are not frozen into config (only custom pins
  are preserved), and `up`/`init` compare the bridge binary version and
  auto-update — a plain pip upgrade picks up new pins (E.7)
- **Nav2 preset (`sim nav2-diffbot`)**: Gazebo diffbot + gpu_lidar +
  slam_toolbox + Nav2 (full stack, default bridge); `/navigate_to_pose` goals
  from the Mac 3/3 SUCCEEDED. `rosmac sim` resets the bridge session on startup
  to prevent action-discovery failures caused by stale routes left by a
  previous stack (KI-17). Launch reliability via stagger timing.
  `viz --layout nav2`.
- **Preset `mac_env_pkgs`**: `rosmac sim` auto-installs the msg packages needed
  to send action goals from the Mac into the Mac conda env (idempotent,
  `deps.ensure_installed`). For nav2 that is nav2_msgs — removes the pitfall
  where goals silently failed with "server not available". (E.17/E.20)

### Verified by measurement (Phase 0/2/4 gates)
- Bridge throughput 10.3 MB/s (1 MB @ 10 Hz, lossless); MoveGroup action
  round-trip SUCCEEDED 3 times in a row
- Gazebo Fortress headless RTF 1.00 (physics) / 0.99 (camera 320x240 @ 15 Hz)
- External-workspace E2E (deps → build → ps → push) completed unattended in 38 s

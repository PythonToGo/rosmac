# Third-Party Notices

rosmac itself is licensed under the [MIT License](LICENSE). This file records
third-party material that is **redistributed in this repository** (and in the
published wheel), plus components that rosmac downloads or expects the user to
install at runtime.

> Status: **draft** (Phase 6.3 review, 2026-08-31). Upstream commit pins and full
> license texts under `LICENSES/` still need to be added before public release —
> Apache-2.0 §4 requires shipping a copy of the license with a derivative work.

---

## 1. Redistributed in this repository (derivative works)

These files are adaptations of upstream ROS / Gazebo example code. Each carries
an attribution header; the summary is here.

### `src/rosmac/assets/presets/gazebo-diffbot/`

| File | Upstream | License | Modification |
|---|---|---|---|
| `diffbot.launch.py` | `ros_gz_sim_demos` — [gazebosim/ros_gz](https://github.com/gazebosim/ros_gz) (`diff_drive.launch.py`) | Apache-2.0 | Removed RViz; headless Gazebo server (`-s --headless-rendering`); bundled world; `/cmd_vel`·`/odom`·`/camera` remaps |
| `diffbot_camera.sdf` | Gazebo Sim `diff_drive.sdf` example — [gazebosim/gz-sim](https://github.com/gazebosim/gz-sim) | Apache-2.0 | Added `ogre2` sensors system + a 320×240@15 Hz front camera on `vehicle_blue` |

### `src/rosmac/assets/presets/nav2-diffbot/`

| File | Upstream | License | Modification |
|---|---|---|---|
| `nav2-diffbot.launch.py` | composed from `ros_gz`, `slam_toolbox`, `nav2_bringup` launch APIs | Apache-2.0 | Original composition; calls into the above projects' launch files |
| `nav2_world.sdf` | Gazebo Sim `diff_drive.sdf` example — [gazebosim/gz-sim](https://github.com/gazebosim/gz-sim) | Apache-2.0 | Walled arena; `gpu_lidar` sensor added; single robot |

### `src/rosmac/assets/presets/panda-moveit/`

| File | Upstream | License | Modification |
|---|---|---|---|
| `demo_headless.launch.py` | `moveit_resources_panda_moveit_config` `demo.launch.py` + `moveit_configs_utils` — [moveit/moveit_resources](https://github.com/moveit/moveit_resources), [moveit/moveit2](https://github.com/moveit/moveit2) | BSD-3-Clause | Removed the `rviz2` and warehouse (MongoDB) nodes for headless operation; parameters unchanged |

### `examples/pick_demo/`

Original code. The joint target values in `pick_demo.py` are the
`ready` / `extended` group states from `panda.srdf` in
[moveit/moveit_resources](https://github.com/moveit/moveit_resources)
(BSD-3-Clause) — reproduced as numeric configuration data.

---

## 2. Runtime Python dependencies (installed by pip, **not** redistributed)

Declared in `pyproject.toml`; pip fetches them from PyPI at install time.

| Package | License |
|---|---|
| [typer](https://github.com/fastapi/typer) | MIT |
| [rich](https://github.com/Textualize/rich) | MIT |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT |
| [pydantic](https://github.com/pydantic/pydantic) | MIT |

---

## 3. Downloaded or user-installed at runtime (**not** redistributed)

rosmac fetches or expects these; none of their code lives in this repo.

| Component | How rosmac uses it | License |
|---|---|---|
| [zenoh-plugin-ros2dds / zenoh-bridge-ros2dds](https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds) | Binary downloaded by `rosmac init`, pinned by version + SHA-256 in `src/rosmac/config.py`, verified before use | EPL-2.0 OR Apache-2.0 |
| [RoboStack](https://github.com/RoboStack/ros-humble) ROS 2 Humble packages | Installed into a conda env by `rosmac init` via micromamba | Per-package (mostly Apache-2.0 / BSD-3-Clause); ROS 2 core is Apache-2.0 |
| [Lima](https://github.com/lima-vm/lima) | `brew install lima` (user runs), driven via `limactl` | Apache-2.0 |
| [micromamba](https://github.com/mamba-org/mamba) | `brew install micromamba` (user runs) | BSD-3-Clause |
| Ubuntu 22.04 cloud image | Downloaded by Lima when creating the VM | Ubuntu / per-package |
| ROS 2 Humble (apt, inside the VM) | Installed by the VM provisioning scripts | Apache-2.0 / per-package |
| [Foxglove](https://foxglove.dev) desktop app | User installs separately; rosmac only opens a deep link | Proprietary (free tier) — not bundled |

---

## Remaining before public release

- [ ] Add `LICENSES/Apache-2.0.txt` and `LICENSES/BSD-3-Clause.txt` (full texts)
- [ ] Pin the upstream commit/tag each derived file was adapted from
- [ ] Include this file in the wheel (`pyproject.toml` — hatch force-include)
- [ ] Confirm `ros_gz` / `gz-sim` example licenses against the exact files used
      (spot-checked as Apache-2.0)

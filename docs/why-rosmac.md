# Why rosmac? (and why not just use Docker)

[한국어 문서는 준비 중입니다.]

ROS 2 does not really support macOS. Under [REP‑2000][rep2000], Ubuntu 22.04
arm64 is **Tier 1** (binaries + CI); macOS is **Tier 3** (Intel source builds
only), and Apple Silicon isn't listed at all. The barriers are OS‑level — SIP
blocking `DYLD_*`, the Homebrew dependency chain, the OGRE/OpenGL stack — not
something a build target fixes.

Every common workaround hits a wall. This page is the honest comparison, with a
measured or documented reason for each wall.

## The alternatives and where they stop

| Approach | Where it breaks |
|---|---|
| **Docker, amd64 image** | Rosetta emulation tax on everything; no GPU; GUI needs an X server; and DDS discovery still breaks at the container boundary — Docker Desktop on macOS has no `--network=host`.[^dockerhost] |
| **Docker, arm64 image + XQuartz** | Native speed, but RViz/Gazebo GUIs over X11 are unstable, and your whole dev loop (editor, debugger, files) is now trapped inside the container. |
| **RoboStack alone (Mac‑native only)** | Ships a surprising amount for osx‑arm64, but the heavy stack (MoveIt, Gazebo full) is *present but not dependable* — dylib breakage[^dylib] and runtime crashes are field‑measured. RViz2 fails structurally on macOS, Intel included.[^rviz929] |
| **Full VM (UTM / Parallels / plain Lima)** | Works, but now you *develop* inside the VM too: IDE integration, file sharing and native performance all regress, and GUI apps come through a streaming bottleneck. |
| **Mac‑native + a VM, connected over DDS** | DDS discovery uses multicast, which does not cross the VM's NAT boundary. This is exactly where the "hybrid" attempts stall. |
| **rosmac (layer split)** | Develop natively on the Mac; run the heavy stack where it's Tier 1 (Lima VM); connect the two with one `zenoh-bridge-ros2dds` hop over a single TCP port (7447), so nothing depends on DDS multicast at the boundary; visualize with Foxglove (native macOS app) reading VM DDS directly. |

The idea isn't novel — people have tried Mac‑native + VM before. What was
missing was **productizing the boundary** (`rosmac up` manages a matched pair of
bridges idempotently) and **productizing the failure modes** (a database of 30
field‑measured macOS/ROS pitfalls wired into `rosmac doctor` / `--fix` /
`report`).

## What we measured (M3 Pro, 2026‑07)

- Bridge throughput: **10.3 MB/s** (1 MB @ 10 Hz, no drops)
- MoveGroup action round‑trip: plan+execute, **3/3 goals SUCCEEDED** from the Mac
- Nav2 `/navigate_to_pose` from the Mac: **3/3 goals SUCCEEDED** (full stack,
  default bridge)
- Gazebo Fortress headless RTF: **1.00** physics‑only, **0.99** with a
  320×240 @ 15 Hz camera
- Camera stream over the bridge: **14.4 fps → 14.4 fps**, lossless

Full numbers and evidence: [PLAN.md](../PLAN.md) risk register (R1, R3, R4 all
marked resolved by measurement) and `docs/plan/phase*-results.md`.

## Limits — honest positioning

rosmac is not magic. It costs you:

- **A VM resident in RAM.** ~2–4 GB while the heavy stack runs. Fine on 16 GB+,
  tight below that.
- **One bridge hop for every Mac↔VM message.** Great for dev, teleop and
  visualization. High‑rate closed control loops belong *inside* the VM (or on
  the robot), not across the bridge.
- **No GPU acceleration in the VM.** Gazebo renders in software (EGL). Adequate
  for the presets; GPU passthrough is an open experiment (Phase 3).
- **Humble only.** Ubuntu 22.04 arm64 pairing. Jazzy and newer are a v0.2+
  backlog item, not supported today.
- **`ros2 param` CLI and `ros2 node list` don't see VM nodes.** The bridge
  mirrors topics/services/actions, not the node graph. Raw parameter *services*
  work.
- **Apple Silicon only.** Intel Macs are explicitly unsupported — there's no way
  to verify them.

## The horizon

Native macOS ROS 2 is improving (Kilted + Gazebo Ionic native demos, late
2025). rosmac's answer is to absorb that, not fight it: run natively what runs
natively, use the VM only for what doesn't. Humble is LTS until 2027, and the
pitfall database keeps its value regardless of distro. Reassessed quarterly
(PLAN.md risk R11).

[rep2000]: https://www.ros.org/reps/rep-2000.html
[^dockerhost]: Docker Desktop for Mac runs containers inside its own Linux VM,
    so `--network=host` binds to that VM, not to macOS. Host↔container DDS
    discovery is broken by design — the same boundary problem rosmac solves with
    the zenoh bridge, just without the tooling.
[^dylib]: RoboStack `ros-noetic#459` is the reference case: a Gazebo plugin
    shipped linked against an older `libprotobuf` than conda‑forge provides, so
    `dlopen` fails at plugin load. rosmac's `doctor` carries fingerprints for
    this class; see `docs/plan/known-issues.md` KI‑2.
[^rviz929]: [ros2/rviz#929](https://github.com/ros2/rviz/issues/929) — RViz2
    fails on macOS, reproduced on Intel Macs too, so it is not an Apple‑Silicon
    issue. This is why rosmac treats Foxglove as the first‑class visualizer
    (decision D4).

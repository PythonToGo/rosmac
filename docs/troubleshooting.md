# Troubleshooting

[한국어 문서는 준비 중입니다.]

**First step, always: `rosmac doctor`.** It runs 16+ checks for exactly these
failure modes and prints the fix. `rosmac doctor --fix` auto-repairs the safe
ones (hung ros2 daemon, orphan bridges, missing Lima UDP rules).

If you're still stuck, find your error string below. Each entry is
**symptom → cause → fix**. For filing an issue, attach a `rosmac report` bundle.

The internal, exhaustive database is
[docs/plan/known-issues.md](plan/known-issues.md) (30+ entries, Korean).

---

## `ros2 topic echo` / `list` hangs forever

**Cause:** the ROS 2 daemon is hung (a known macOS failure mode).

**Fix:**

```bash
rosmac doctor --fix      # detects it as C12 and restarts the daemon
# or manually, inside `rosmac shell`:
ros2 daemon stop && ros2 daemon start
```

---

## Topics appear only sometimes, or topics from other machines on your LAN leak in

**Cause:** a ROS process (often the bridge) was started from a bare shell
without `ROS_LOCALHOST_ONLY=1`, so DDS multicast escaped to the real network.

**Fix:** only ever start ROS processes through `rosmac` (`rosmac up`,
`rosmac shell`, `rosmac sim`). `rosmac doctor` C4 flags a leaked environment.
Then restart cleanly:

```bash
rosmac down --keep-vm && rosmac up
```

---

## The same message is received twice (`ros2 topic hz` shows exactly 2×)

**Cause:** a bridge that exited uncleanly (SIGKILL) left stale routes on the
other side; the new bridge session double-routes.

**Fix:**

```bash
rosmac down --keep-vm && rosmac up      # restarts both bridges, clears session state
```

Always stop the stack with `rosmac down`, never `kill -9`.

---

## Services or actions time out, but topics work

Server stderr shows:

```
[RTPS_READER_HISTORY Error] Change payload size of '36' bytes is larger than
the history payload size of '23' bytes and cannot be resized
```

**Cause:** Fast DDS (the default RMW) rejects the bridged service-request
payload. This is why rosmac pins `rmw_cyclonedds_cpp` on **both** sides.

**Fix:** `rosmac doctor` C4 checks the RMW. If it's wrong, your environment is
overriding it — unset `RMW_IMPLEMENTATION` and use `rosmac shell`. VM side:
`sudo apt install ros-humble-rmw-cyclonedds-cpp` (rosmac's provisioning does
this already; a hand-modified VM may have lost it — see the next entry).

---

## Something in the VM "reverts" after every reboot

**Cause:** Lima re-runs its provisioning scripts on **every boot**, not once.
Manual edits to systemd units or configs inside the VM get overwritten.

**Fix:** put permanent changes in the provisioning assets in the repo and
recreate the VM, or patch `~/.lima/<vm>/lima.yaml` too. For a hand-tweaked VM,
the clean path is:

```bash
rosmac down && limactl delete rosmac && rosmac init && rosmac up
```

---

## A node dies with a "participant index" error

```
Failed to find a free participant index for domain 0
rmw_create_node: failed to create domain
```

Common tell: a MoveIt/Nav2 action goal fails in tens of milliseconds with
"Solution found but controller failed during execution".

**Cause:** CycloneDDS defaults to 10 DDS participants per host; the bridge +
stack + CLI exceed it.

**Fix:** rosmac ships a CycloneDDS config that raises the cap and injects it
into every execution path. If you see this, some process isn't getting the
config:

```bash
rosmac doctor            # C4 / C13 area
# verify the bridge has it:
cat /proc/$(pgrep -x zenoh-bridge-ro)/environ | tr '\0' '\n' | grep CYCLONE
```

If the bridge unit is missing `CYCLONEDDS_URI`, recreate the VM (previous entry).

---

## `ros2 run <pkg> <exe>` → "No executable found" (build succeeded)

The executable is under `install/<pkg>/bin/` instead of `install/<pkg>/lib/<pkg>/`.

**Cause:** recent setuptools installs console scripts into `bin/`; `ros2 run`
only looks in `lib/<pkg>/`.

**Fix:** add to the package's `setup.cfg` (see `examples/pick_demo/setup.cfg`):

```ini
[develop]
script_dir=$base/lib/<pkg>
[install]
install_scripts=$base/lib/<pkg>
```

---

## Build fails with `Could NOT find Python` (Python and NumPy are installed)

Happens for packages containing `.msg` / `.srv` / `.action` files; pure
`rclcpp` packages in the same workspace build fine.

**Cause:** an outdated `cmake_minimum_required(VERSION 3.5)` pins CMake policies
so old that `FindPython` misses the conda (macOS) interpreter.

**Fix:** build inside `rosmac shell` — it injects the workaround automatically.
Outside it:

```bash
colcon build --cmake-args -DCMAKE_POLICY_DEFAULT_CMP0094=NEW
```

Keep `cmake<4` in the env (rosmac's env list already does).

---

## `ros2 launch` dies with a substitution repr instead of a name

```
executable '[<launch.substitutions.text_substitution.TextSubstitution object at 0x...>]'
not found on the PATH
```

**Cause:** the launch file calls `FindExecutable(name='xacro')` (or similar) and
that executable isn't in the env. RoboStack's `ros-humble-desktop` doesn't
include `xacro`, unlike the apt version.

**Fix:**

```bash
micromamba install -n ros_env -c conda-forge -c robostack-humble ros-humble-xacro
```

`rosmac deps` can't catch this class — executables used without a `package.xml`
declaration slip through. `rosmac doctor` C13 checks for `ros2`/`colcon`/`xacro`.

---

## `ros2: command not found` in `rosmac shell --vm -c '...'` (interactive VM shell is fine)

**Cause:** Ubuntu's default `.bashrc` returns early for non-interactive shells,
before the ROS `source` line at the end.

**Fix:** prefix your VM command explicitly:

```bash
rosmac shell --vm -c 'source /opt/ros/humble/setup.bash && ros2 ...'
```

---

## Mac ↔ VM topics suddenly stop flowing (worked earlier today)

`rosmac up` still reports the bridges as connected (that's a TCP check — it
passes even when DDS discovery is broken).

**Cause:** another Lima VM without UDP-ignore rules is hijacking `127.0.0.1`
DDS ports via Lima's automatic port forwarding, starving the Mac's local DDS
discovery.

**Fix:**

```bash
rosmac doctor            # C17 flags the offending 127.0.0.1:74xx bind
lsof -nP -iUDP:7400-7440 | grep limactl     # confirm which VM
```

rosmac's own VM is safe (it ships the rules). The culprit is a *different* or
older Lima VM — apply UDP-ignore rules to its `lima.yaml` and restart (or stop)
it, then:

```bash
# clear the poisoned CLI participants left behind:
rosmac shell -c 'ros2 daemon stop'
rosmac doctor            # C8 should pass again — no reboot needed
```

---

## Foxglove can't connect / handshake fails

Bridge log:

```
foxglove::websocket::server] Dropping client ...: handshake failed
HTTP 400 — Missing expected sec-websocket-protocol header
```

**Cause:** `foxglove_bridge` 3.4+ changed its WebSocket subprotocol to
`foxglove.sdk.v1`. The header is present; the value is different.

**Fix:** the Foxglove **desktop app** (recent versions) negotiates
automatically — update the app. Custom scripts must connect with
`subprotocols=["foxglove.sdk.v1"]`.

---

## `micromamba create` can't find ROS packages

```
nothing provides ros-humble-desktop
```

**Cause:** the RoboStack channel name has changed over time
(`robostack-staging` ↔ `robostack-humble`); an old guide pointed you at the
wrong one.

**Fix:** rosmac pins `robostack-humble` in `src/rosmac/config.py`. If upstream
moved it, the weekly drift-check CI job will have filed an issue — check
<https://github.com/PythonToGo/rosmac/issues>. Don't hand-edit the channel;
`pip install -U rosmac` picks up corrected pins.

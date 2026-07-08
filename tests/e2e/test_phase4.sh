#!/usr/bin/env bash
# Phase 4 E2E — "처음 보는 외부 워크스페이스" 시나리오 (phase4-features.md 4.5)
#   deps 분석/설치 → 무플래그 colcon 빌드(KI-25 자동 우회) → ps 관찰 →
#   linux 전용 패키지 push+VM 빌드·실행 → 정리
# 전제: rosmac init 완료, VM 존재. 브리지 토픽 경유 단계 없음 (KI-28과 무관).
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
ROSMAC="$ROOT/.venv/bin/rosmac"
PY="$ROOT/.venv/bin/python"
FIX="$ROOT/tests/fixtures"
TMP=$(mktemp -d /tmp/rosmac-p4e2e.XXXXXX)
VM_WS_NAME="e2e-linux"
trap 'rm -rf "$TMP"' EXIT
export MAMBA_ROOT_PREFIX="${MAMBA_ROOT_PREFIX:-$HOME/micromamba}"

step() { echo; echo "━━ $1"; }
t0=$(date +%s)

step "0. VM 기동 (멱등)"
"$ROSMAC" up >/dev/null

step "1. 외부 프로젝트 구성 (픽스처 조립)"
mkdir -p "$TMP/ws/src" "$TMP/build_ws/src" "$TMP/linux_ws/src"
cp -r "$FIX/deps_ws/src/"* "$TMP/ws/src/"
mkdir -p "$TMP/ws/src/gamma"
cat > "$TMP/ws/src/gamma/package.xml" <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>gamma</name><version>0.0.1</version>
  <description>e2e missing-dep probe</description>
  <maintainer email="e2e@rosmac">e2e</maintainer><license>MIT</license>
  <depend>topic_tools</depend>
</package>
EOF
cp -r "$FIX/legacy_msgs" "$TMP/build_ws/src/"
cp -r "$FIX/linux_only_pkg" "$TMP/linux_ws/src/"
echo "ok"

step "2. rosmac deps — missing 검출 → --install → 해소"
micromamba remove -n ros_env -y ros-humble-topic-tools >/dev/null 2>&1 || true
"$ROSMAC" deps "$TMP/ws" --json > "$TMP/deps1.json"
"$PY" - "$TMP/deps1.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
assert "ros-humble-topic-tools" in d["missing"], d["missing"]
assert d["unknown"] == ["libweird-system-dev"], d["unknown"]
assert d["unavailable"] == ["ros-humble-totally-fake-ros-pkg-xyz"], d["unavailable"]
assert "beta" not in " ".join(d["missing"] + d["installed"])  # ws 내부 제외
print("  deps 1차 분류 ✓")
EOF
"$ROSMAC" deps "$TMP/ws" --install --json > "$TMP/deps2.json"
"$PY" - "$TMP/deps2.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["missing"] == [], d["missing"]
assert "ros-humble-topic-tools" in d["installed"]
print("  deps --install 해소 ✓")
EOF

step "3. 무플래그 colcon 빌드 (legacy_msgs — KI-25 자동 우회)"
"$ROSMAC" shell -c "cd $TMP/build_ws && colcon build" 2>/dev/null | grep -q "1 package finished" \
  && echo "  legacy_msgs 빌드 ✓"

step "4. rosmac ps — 경고 0"
"$ROSMAC" ps --json > "$TMP/ps.json"
"$PY" - "$TMP/ps.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["warnings"] == [], d["warnings"]
assert d["vm_state"] == "Running", d["vm_state"]
print("  ps 경고 0 ✓ (VM Running)")
EOF

step "5. rosmac push --build → VM 실행"
"$ROSMAC" push "$TMP/linux_ws" --name "$VM_WS_NAME" --build | grep -q "Finished <<< linux_only_pkg" \
  && echo "  VM 빌드 ✓"
limactl shell rosmac -- bash -c \
  "source /opt/ros/humble/setup.bash && source ~/rosmac-ws/$VM_WS_NAME/install/setup.bash && ros2 run linux_only_pkg epoll_node" \
  | grep -q "epoll fd=" && echo "  VM 실행 ✓"

step "6. 정리"
limactl shell rosmac -- bash -c "rm -rf ~/rosmac-ws/$VM_WS_NAME" && echo "  VM ws 제거 ✓"
"$ROSMAC" ps --json | "$PY" -c "import json,sys; d=json.load(sys.stdin); assert d['warnings']==[], d['warnings']; print('  잔여 경고 0 ✓')"

echo
echo "ALL PASS ($(( $(date +%s) - t0 ))s)"

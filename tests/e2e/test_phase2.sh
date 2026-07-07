#!/bin/bash
# Phase 2 E2E (phase2 2.7) — Foxglove 육안 항목 제외 전 단계 스크립트화.
# 전제: rosmac init 완료 상태 (Phase 1 E2E와 달리 환경을 지우지 않는다).
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO="$PWD"
export PATH="$REPO/.venv/bin:$PATH"
export MAMBA_ROOT_PREFIX="${MAMBA_ROOT_PREFIX:-$HOME/micromamba}"

T0=$(date +%s)
echo "== P2E2E-0. 깨끗한 시작 (sim/브리지 재기동) =="
rosmac sim stop || true
rosmac down --keep-vm || true

echo "== P2E2E-1. rosmac up --viz =="
rosmac up --viz

echo "== P2E2E-2. rosmac sim panda-moveit → READY =="
rosmac sim panda-moveit --no-viz

echo "== P2E2E-3. 맥 빌드 (colcon) =="
rosmac shell -c "cd $REPO/examples && colcon build" > /dev/null
echo "build ok"

echo "== P2E2E-4/5. pick_demo 3-goal 순회 =="
OUT=$(rosmac shell -c "source $REPO/examples/install/setup.bash && ros2 run pick_demo pick_demo" || true)
echo "$OUT" | tail -3
echo "$OUT" | grep -q "3/3 SUCCEEDED" \
  && echo "P2E2E-5 PASS" || { echo "P2E2E-5 FAIL"; exit 1; }

echo "== P2E2E-6. 정리: sim stop + down =="
rosmac sim stop
rosmac down
sleep 2
pgrep -f zenoh-bridge-ros2dds && { echo "P2E2E-6 FAIL: bridge alive"; exit 1; } \
  || echo "P2E2E-6 PASS (잔여 0)"
T1=$(date +%s)
echo "P2E2E-TOTAL: $((T1-T0))s — ALL PASS"

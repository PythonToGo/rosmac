#!/bin/bash
# rosmac E2E 수용 테스트 (phase1 1.8)
# ⚠️ 파괴적: lima VM 'rosmac'과 conda env 'ros_env'를 삭제하고 처음부터 재구축한다.
# macOS에 GNU timeout이 없어 문서 스니펫의 `timeout N`을 perl alarm으로 대체 (KI 기록).
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="$PWD/.venv/bin:$PATH"
export MAMBA_ROOT_PREFIX="${MAMBA_ROOT_PREFIX:-$HOME/micromamba}"

echo "== E2E-0. 초기화 (삭제 대상: lima VM 'rosmac', conda env 'ros_env') =="
limactl delete -f rosmac 2>/dev/null || true
micromamba env remove -n ros_env -y 2>/dev/null || true
# 브리지는 프로세스까지 정리 (pidfile만 지우면 고아가 남아 새 브리지가 포트 충돌로 즉사 — KI-20)
pkill -f "$HOME/.rosmac/bin/zenoh-bridge" 2>/dev/null || true
rm -f ~/.rosmac/run/bridge.pid

T0=$(date +%s)
echo "== E2E-1. rosmac init (깨끗한 상태) =="
rosmac init
echo "== E2E-2. rosmac up =="
rosmac up
echo "== E2E-3. VM talker 기동 =="
rosmac shell --vm -c 'nohup ros2 run demo_nodes_cpp talker > /tmp/talker.log 2>&1 & sleep 1; echo talker_started'
sleep 8
echo "== E2E-4/5. 맥에서 /chatter 수신 판정 =="
OUT=$(rosmac shell -c 'perl -e "alarm 30; exec @ARGV" ros2 topic echo /chatter --once' || true)
echo "$OUT" | grep -q "Hello World" \
  && echo "E2E-5 PASS" || { echo "E2E-5 FAIL: $OUT"; exit 1; }
echo "== E2E-5b. hz 중복 검사 (KI-17 회귀) =="
HZ=$(rosmac shell -c 'perl -e "alarm 15; exec @ARGV" ros2 topic hz /chatter 2>&1 | grep -m1 "average rate"' || true)
echo "hz: $HZ"
RATE=$(echo "$HZ" | grep -oE '[0-9]+\.[0-9]+' | head -1)
python3 -c "import sys; r=float('${RATE:-0}'); sys.exit(0 if 0.8 <= r <= 1.2 else 1)" \
  && echo "E2E-5b PASS (rate=$RATE)" || { echo "E2E-5b FAIL: rate=$RATE (중복/유실 의심)"; exit 1; }
echo "== E2E-6. doctor =="
rosmac doctor
echo "== E2E-7. down + 잔여 프로세스 판정 =="
rosmac shell --vm -c 'pkill -f "[d]emo_nodes" || true; echo cleanup_ok'
rosmac down
sleep 2
pgrep -f zenoh-bridge-ros2dds && { echo "E2E-7 FAIL: bridge alive"; exit 1; } \
  || echo "E2E-7 PASS"
T1=$(date +%s)
echo "E2E-TOTAL: $((T1-T0))s — ALL PASS"

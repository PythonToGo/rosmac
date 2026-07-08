# E2E 테스트 — **로컬 전용** (CI 불가, 실측 확정)

GitHub Actions macOS 러너(macos-14, arm64)는 **nested virtualization을 지원하지
않는다** — 2026-07-08 실측(e2e-probe.yml run 28972640343): 러너에 `kern.hv_support`
sysctl oid 자체가 없고, `limactl start`가 부팅 중 fatal로 종료(Running 도달 실패).
따라서 Lima VM이 필요한 E2E는 CI에서 돌 수 없고, 아래 절차로 로컬에서 실행한다.

## 실행 절차 (Apple Silicon 맥)

전제: `rosmac init` 완료 상태 (README Quickstart).

```bash
# 스모크 (~1분): up → 토픽 왕복 → down
bash tests/e2e/test_smoke.sh

# Phase 2 시나리오: sim 프리셋 기동 → health → viz
bash tests/e2e/test_phase2.sh

# Phase 4 시나리오 (~40초): 외부 워크스페이스 deps → 빌드 → ps → push
bash tests/e2e/test_phase4.sh
```

- pytest 마커로도 실행 가능: `pytest tests/e2e -m e2e` (VM 실기동 필요)
- 실행 시점: 릴리스 태깅 전, VM 템플릿/브리지 버전 핀 변경 후 (P5.5/5.6 게이트)
- CI가 대신 커버하는 것: lint/type/unit/설치 스모크(ci.yml),
  업스트림 드리프트(weekly.yml — RoboStack env 실생성 + 브리지 자산 sha)

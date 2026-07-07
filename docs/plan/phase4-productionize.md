# Phase 4 — 제품화 (릴리스 엔지니어링·견고성)

> 목표: "내 맥에서 돌아가는 도구"를 **모르는 사람이 자기 맥에 설치해서 성공하는 제품**으로.
> 착수 조건: Phase 2 완료 (충족됨). Phase 3(GPU)과 독립 — 병행 가능.
> E2E 성공 기준: **rosmac을 한 번도 설치한 적 없는 macOS 계정**에서
> `pipx install rosmac`(또는 TestPyPI) → README Quickstart만 보고 →
> Phase 2 E2E(sim panda-moveit + 맥 제어 노드) 통과.
> 예상 소요: 2~3주 (파트타임)

## 태스크 의존 그래프

```
4.1 지원 매트릭스·버전 정책 ─→ 4.5 패키징·배포 ─→ 4.6 프레시 머신 검증 (게이트)
4.2 CLI 견고성 ──────────────┤
4.3 doctor 강화 + report ────┤
4.4 CI 파이프라인 ───────────┘
```

4.1~4.4는 상호 독립(순서 자유), 4.5가 이들을 묶고, 4.6이 최종 게이트다.

---

## 4.1 지원 매트릭스·버전 정책

### 절차
1. 공식 지원 선언을 문서화 (README + doctor C1 경고 기준):
   - HW: Apple Silicon (M1 이상). Intel Mac은 **명시적 비지원** (검증 수단 없음)
   - OS: macOS 14 (Sonoma) 이상 — 실측은 26.x, 하한은 Lima 요구사항 기준으로 확정
   - Python: 3.11+ (실측 3.12)
2. SemVer 채택 (D12): `0.y.z` 동안은 마이너가 breaking 가능함을 명시.
   `src/rosmac/__init__.py`에 `__version__` 단일 소스 → `rosmac --version`.
3. `CHANGELOG.md` 생성 (Keep a Changelog 형식) — Phase 0~2 요약을 `[0.1.0] - Unreleased`로 소급 기록.

### 완료 기준 (AC)
- [ ] `rosmac --version` 이 pyproject 버전과 일치 (단일 소스 확인 테스트 포함)
- [ ] README에 지원 매트릭스 표 존재
- [ ] CHANGELOG.md 존재 + 규약이 CONTRIBUTING(Phase 5)에서 참조 가능한 형태

---

## 4.2 CLI 견고성 (production hardening)

### 배경
현재 CLI는 정상 경로는 튼튼하지만(E2E 검증), 비정상 경로의 UX가 제품 수준이 아니다:
스택트레이스 노출 가능성, exit code 미규약, non-TTY 미고려, 제거 수단 부재.

### 절차
1. **exit code 규약**: 0 성공 / 1 실행 실패 / 2 사용법·설정 오류. 표를 docs에 명시,
   모든 커맨드 핸들러에서 예외 → `RosmacError`(메시지+처방) → rich 패널 출력으로 통일.
   예상 밖 예외만 traceback (+ "rosmac report로 이슈 첨부" 안내).
2. **non-TTY 안전**: `rosmac status | cat`, CI 환경(`TERM=dumb`)에서 깨지지 않음.
   rich는 자동 폴백하지만 progress/스피너 사용처를 전수 점검.
3. **`rosmac uninstall`**: conda env / VM / `~/.rosmac` / (안내) Foxglove 앱 순서로 제거.
   각 대상 경로를 출력하고 개별 y/n 확인, `--yes`로 일괄. (절대 규칙 7 준수 지점)
4. **부분 초기화 상태 방어**: init 안 된 상태에서 up/sim 실행 → "rosmac init 먼저" 한 줄 안내
   (현재 동작 전수 확인 후 누락분 보강).

### 완료 기준 (AC)
- [ ] exit code 표 문서화 + 대표 실패 시나리오 3개(로그아웃된 VM, env 없음, 잘못된 프리셋)에서 실측 일치
- [ ] `rosmac status | cat` 및 `TERM=dumb rosmac doctor` 정상 출력
- [ ] `rosmac uninstall --yes` 후 `~/.rosmac`·env·VM 잔재 0 → 직후 `rosmac init`으로 완전 재설치 성공

---

## 4.3 doctor 강화 + `rosmac report`

### 배경
RCM 지원 세션(2026-07-07)에서 실사용자가 겪은 3대 장애 — ros2 데몬 hang,
VM sim 잔존 토픽 오염, zenoh 브리지 낡은 라우트 — 는 전부 **doctor가 감지 못 하는**
유형이었다. 제품화의 핵심은 "막혔을 때 스스로 빠져나올 수 있는가"다.

### 절차
1. 신규 체크: C12 ros2 데몬 응답성 (XMLRPC 5초 타임아웃 — 실측 검증된 방법),
   C13 필수 실행파일 존재 (xacro 등, KI-26), C14 그래프 오염 감지
   (기대 밖 `/robot_description`/`/tf` 발행자 경고 — sim 안 돌 때).
2. **`rosmac doctor --fix`**: 자동 처방이 안전한 항목만 —
   데몬 재시작, 고아 브리지 sweep(KI-20), 인스턴스 lima.yaml의 KI-24 패치 누락 보정.
   각 fix는 실행 전 무엇을 하는지 출력. 수리 불가 항목은 처방 명령만 출력(현행 유지).
3. **`rosmac report`**: 이슈 첨부용 진단 번들 생성 —
   `doctor --json` + 버전 매트릭스(macOS/lima/micromamba/브리지/채널) +
   `~/.rosmac/log/` 최근 로그 + VM 유닛 상태 → `rosmac-report-<날짜>.tar.gz`.
   **개인정보 주의**: 홈 경로 외 파일 수집 금지, 수집 목록을 생성 시 출력.

### 완료 기준 (AC)
- [ ] 데몬을 인위적으로 SIGSTOP → `doctor`가 C12 FAIL 감지 → `doctor --fix`가 복구 (실측)
- [ ] 고아 브리지 시나리오(KI-20 재현 절차)에서 `--fix` 복구 실측
- [ ] `rosmac report` 산출물을 풀어 내용물 검증 (로그/버전/JSON 포함, 홈 밖 파일 없음)

---

## 4.4 CI 파이프라인

### 배경/제약
GitHub Actions macOS 러너(macos-14/15, arm64)는 **nested virtualization이 제한적**이라
Lima VM 기동(E2E)은 러너에서 불가할 가능성이 높다 — 실측 후 판정하고, 불가면
E2E는 로컬 수동 실행으로 남기되 실행 절차를 CI 문서에 명시한다.

### 절차
1. `ci.yml`: PR/push마다 — ruff(lint+format check), pytest unit, `pip install -e .` 스모크,
   `rosmac --help`/`--version` 실행 확인. (macos-14 + ubuntu 조합, ubuntu에선 문법·unit만)
2. `weekly.yml` (cron, R7 완화): macOS 러너에서 `micromamba create` 실제 실행으로
   RoboStack 채널 드리프트 감지 + zenoh-bridge 릴리스 URL/sha 유효성 확인.
   실패 시 GitHub Issue 자동 생성.
3. E2E 러너 실측: macOS 러너에서 `limactl start` 시도 → 결과를 phase4-results.md에 기록,
   불가 판정이면 `tests/e2e/README`에 "로컬 전용" 명시.

### 완료 기준 (AC)
- [ ] PR에서 ci.yml green (의도적 lint 오류 커밋으로 red도 확인)
- [ ] weekly.yml 수동 트리거 1회 성공 + 실패 경로(가짜 URL) 테스트로 이슈 생성 확인
- [ ] E2E-in-CI 가능 여부 실측 기록

---

## 4.5 패키징·배포

### 절차
1. **이름 확보**: PyPI `rosmac` 가용성 확인. 선점돼 있으면 대안(`rosmac-cli` 등)을
   사용자와 결정(에스컬레이션 대상) 후 pyproject/문서 일괄 반영.
2. pyproject 메타데이터 완성: description, classifiers(OS::MacOS, Robotics 등),
   urls(repo/docs/issues), license, `requires-python`.
3. 배포 자동화: git tag `vX.Y.Z` → GitHub Actions → build(sdist+wheel) →
   **PyPI Trusted Publishing**(토큰 비보관) → GitHub Release 노트 자동 생성.
4. 검증 순서: TestPyPI에 0.1.0rc를 먼저 올려 `pipx install --index-url ...`로
   Quickstart 전체 통과 → 본 PyPI. **실제 publish 실행은 사용자 승인 후** (절대 규칙 9).
5. (후순위, D10) Homebrew tap `PythonToGo/homebrew-rosmac` — formula가 pipx 대비
   이득이 있는지 평가만 하고 v0.1에선 생략 가능.

### 완료 기준 (AC)
- [ ] 깨끗한 셸에서 `pipx install`(TestPyPI) → `rosmac init → up → doctor` 통과
- [ ] tag → Release+publish 워크플로가 TestPyPI 대상으로 1회 완주
- [ ] 잠금 대상 버전 핀(BRIDGE_VERSION, 채널명, lima 하한)이 릴리스 노트에 자동 포함

---

## 4.6 프레시 머신 재현성 검증 (Phase 4 게이트)

### 절차
1. 이 맥에 **새 macOS 사용자 계정** 생성 (완전 초기 상태 — brew 없음이 이상적이나
   시스템 공유라면 그 사실을 기록하고 변인으로 명시).
2. README Quickstart를 **문서 그대로, 보정 없이** 수행. 막히는 모든 지점을 기록.
3. 걸림돌 각각에 대해: 문서 수정 / 코드 수정 / known-issues 추가 중 하나로 처리.
4. 소요 시간(다운로드 포함/제외)을 README의 예상 시간과 대조·갱신.

### 완료 기준 (AC)
- [ ] 새 계정에서 Quickstart → Phase 2 E2E까지 **문서 외 지식 0으로** 통과
- [ ] 발견된 걸림돌 전부 반영 후 재실행 1회 클린 통과
- [ ] phase4-results.md에 타임라인·버전 기록

## 명시적 비목표
- Linux/Windows 지원, Intel Mac 지원
- ROS2 Humble 외 배포판 (Jazzy 등은 v0.2+ 백로그)
- 텔레메트리/사용 통계 수집 (하지 않는다 — 신뢰 자산)

# Phase 1 결과 리포트 — 2026-07-07

> 진행 중 문서 — E2E(P1.8) 완료 시 확정.

## 0. 실행 환경
- macOS 26.5.2 / Apple M3 Pro / 18GB (Phase 0과 동일 머신)
- 실행 에이전트: Claude Fable 5 (claude-fable-5), 2026-07-07
- 도구: lima=2.1.4 / micromamba=2.8.1 / 개발 python=3.12.9 (Homebrew, venv)
- 의존성 버전: typer/rich/pyyaml/pydantic 최신 (pyproject 하한 준수), pytest/ruff/mypy

## 태스크별 기록

### P1.1 리포 스캐폴딩 — PASS
- AC: [x] `rosmac version` 출력 [x] ruff/pytest 클린 (+mypy) [x] 커밋 `[P1.1]`
- 계획과 다른 것: typer는 커맨드가 1개면 서브커맨드 모드가 풀리므로 no-op `@app.callback()` 추가

### P1.2 config 모듈 — PASS
- AC: [x] 최초 실행 시 기본 config 생성 [x] 검증 실패 시 명확한 에러(ConfigError에 경로+원인)
  [x] 단위 테스트 4케이스 (로드/기본값/검증 실패/YAML 깨짐)
- 핀 값 내장: bridge 1.9.0 + 양 플랫폼 sha256, rmw=rmw_cyclonedds_cpp(D9), channel=robostack-humble

### P1.3 Lima 템플릿 자산화 + lima.py — PASS
- AC: [x] 렌더링된 YAML로 무인 프로비저닝 성공 (Phase 0.2와 동일 + 브리지까지)
  [x] 부팅 직후 `systemctl is-active zenoh-bridge` == active (실측: active, v1.9.0)
  [x] 렌더링 스냅샷 단위 테스트 (subprocess mock)
- 설계: 템플릿은 string.Template 델리미터 `@` (셸 `$` 충돌 회피, 부록 C-3),
  provision 2단계(10-ros2-humble.sh — OSRF 저장소 포함 KI-13 / 20-bridge.sh — 바이너리
  sha256 검증 + systemd 유닛, T9 재연결을 systemd Restart에 위임)
- 참고: 이 커밋에 P1.4~1.6 커맨드 구현이 함께 포함됨 (검증·수정은 각 태스크 커밋에서)

### P1.4 rosmac init — PASS
- AC: [x] init 1회 전 단계 성공 [x] 재실행 시 전부 스킵 (실측: 2회차 각 단계 0.0s)
  [x] VM만 삭제 후 init → VM 단계만 재수행 (E2E-1에서 전체 삭제 후 재구축으로 포괄 검증)
  [x] 소요 시간 로그 (요약 테이블에 단계별 초 표기)
- 안전장치: `limactl start`가 provision 실패에도 exit 0인 문제(Phase 0) →
  init이 `/opt/ros/humble/setup.bash` + systemd active를 후검증

### P1.5 rosmac up/down/status — PASS
- AC: [x] up→status→down→status 표 일치 [x] up 2연속 → 브리지 1개(pidfile)
  [x] kill -9 후 up → 정상 복구(죽은 pidfile 자동 정리) [x] down 후 잔여 0
- 보강: up이 맥 브리지를 새로 띄울 때 VM 브리지를 재시작해 세션 초기화 (KI-17 예방)
- pidfile은 pid 재사용 방어를 위해 cmdline에 zenoh-bridge 포함 여부까지 확인

### P1.6 rosmac doctor — PASS
- AC: [x] 정상 상태 C1~C11 전부 PASS (exit 0)
  [x] 고장 3종이 정확한 항목만 FAIL + 처방:
  - 브리지 kill → C6 FAIL(rosmac up), C8 FAIL(로그 경로)
  - VM 정지 → C2/C7 WARN(rosmac up), C5/C8 FAIL
  - env 부재(config로 시뮬레이션; 실삭제는 E2E-0~1에서 검증) → C3 FAIL(rosmac init)
- 수정 2건:
  - C5 오탐: 맥 브리지(router 모드)가 [::]:7447을 listen해 VM이 꺼져도 TCP 연결이
    성사됨 → VM 상태를 먼저 확인하도록 수정
  - C8: VM 명령이 .bashrc 소싱에 의존 → **KI-19 발견** (비인터랙티브 bash -lc는
    Ubuntu .bashrc early-return으로 ROS 소싱 미도달) → source 명시로 수정
- C9 지문 DB는 빈 목록 (Phase 0에서 깨진 dylib 0건 — R2 발생 시 추가)

### P1.7 rosmac shell — PASS
- AC: [x] `shell -c 'ros2 topic list'` 즉시 동작 (env 주입 확인: ROS_LOCALHOST_ONLY=1,
  rmw_cyclonedds_cpp) [x] `--vm` 동일 (KI-19 대응: -c 모드는 source+env 명시 래핑)
- 인터랙티브 경로는 ZDOTDIR 임시 zshrc로 검증 (ros2가 ros_env 경로로 해석됨)

### P1.8 E2E 수용 테스트 — PASS
- AC: [x] 초기화(VM+env 삭제)→init→up→talker→echo→doctor→down 무인 통과
  [x] 총 소요 **327초** (README "설치 소요" 근거: 패키지 캐시 있는 상태.
  내역: conda env 124s + VM 프로비저닝 170s + 나머지)
  [x] 이 리포트 기록 완료 — Phase 2 착수 게이트
- 스크립트: `tests/e2e/test_smoke.sh` (문서 스니펫 대비 수정: GNU timeout 부재 →
  perl alarm; KI-17 회귀 검사로 hz 0.8~1.2 판정 추가; VM 명령은 rosmac shell --vm -c 경유)
- 판정 상세: E2E-5 "Hello World" 수신 / E2E-5b hz **1.001** (중복 없음) /
  doctor C1~C11 전부 PASS / down 후 잔여 프로세스 0
- 1차 실행 실패 → **KI-20 발견**: 초기화가 pidfile만 지워 고아 브리지가 남았고,
  새 브리지가 [::]:7447 충돌로 즉사 (doctor C6이 정확히 잡음). 제품 수정 2건:
  bridge.start() 즉사 감지(로그 tail 포함 에러), bridge.stop() 고아 정리. 수정 후 재실행 전체 통과

## 다음 페이즈 인계 메모 (Phase 2 실행자에게)
- `rosmac init && rosmac up`만으로 E2E 성립. 진단은 `rosmac doctor` (C8이 최종 왕복 판정)
- VM 쪽 ROS 명령은 반드시 `rosmac shell --vm -c` 경유 (KI-19: bash -lc는 ROS 소싱 안 됨)
- 맥 브리지는 router 모드라 [::]:7447도 listen — Phase 2에서 foxglove/추가 포트 설계 시
  포트 충돌 주의. client 모드 전환은 검토 옵션 (검증 필요)
- 스파이크 VM(rosmac-spike)은 이제 불필요 — 디스크 회수하려면 `limactl delete -f rosmac-spike`
  (사용자 확인 후). 제품 VM은 'rosmac' (Stopped 상태로 보존됨)

# rosmac — macOS(Apple Silicon) ROS2 개발 환경 마스터 플랜

> 최종 수정: 2026-07-07
> 상태: **Phase 2 완료 (E2E ALL PASS) — 제품화 트랙(Phase 4~6) 계획 수립, Phase 3(실험)은 선택**
> 실측 기록: [`docs/plan/phase0-results.md`](docs/plan/phase0-results.md)
>
> **⚠️ 실행 에이전트(모델 무관)는 작업 시작 전에 반드시 [`AGENTS.md`](AGENTS.md)를
> 먼저 읽을 것** — 배경지식, 절대 규칙, 태스크 수행 프로토콜, 에스컬레이션 기준, 용어집.
> 막히면 [`docs/plan/known-issues.md`](docs/plan/known-issues.md)부터 검색.
> 결과 기록 양식: [`docs/plan/templates/phase-results-template.md`](docs/plan/templates/phase-results-template.md)

## 1. 프로젝트 목표

Apple Silicon Mac에서 ROS2 Humble + MoveIt + RViz(대체: Foxglove) + Gazebo 기반
개발이 **명령어 몇 개로** 가능하게 만드는 CLI 도구 `rosmac`을 개발한다.

**최종 목표 (2026-07-07 확장)**: 개인 도구에 그치지 않고 **공개 가능한 제품**으로 —
(a) 오픈소스 릴리스 (PyPI + GitHub public, v0.1.0),
(b) 출판 (JOSS 소프트웨어 페이퍼 + ROSCon 발표 제안),
(c) 포트폴리오 피쳐. Phase 4~6이 이 트랙이다. 공개의 전제는
"모르는 사람의 맥에서 문서만으로 재현"(Phase 4.6 게이트)이며, 이 기준을
통과하지 못한 상태로 공개하지 않는다.

핵심 전략 — **레이어 분리 하이브리드**:

| 레이어 | 실행 위치 | 이유 |
|---|---|---|
| L1 코드 개발/빌드/노드 실행 (rclpy/rclcpp, colcon) | 맥 네이티브 (RoboStack conda) | 빠른 개발 루프, IDE 통합 |
| L2 시각화 | 맥 네이티브 Foxglove (RViz2는 보조) | macOS에서 원래 잘 되는 유일한 시각화 스택 |
| L3 시뮬레이션 + 무거운 스택 (Gazebo, move_group) | Lima VM 내 ARM64 Ubuntu 22.04 | ROS2 Tier 1 플랫폼 = 문서 그대로 100% 동작 |
| L4 경계 연결 (토픽/서비스/액션 투명 전달) | zenoh-bridge-ros2dds (양측) | DDS 멀티캐스트가 VM NAT를 못 넘는 문제의 해법 |

## 2. 아키텍처

```
┌─ macOS (Apple Silicon) ─────────────────────────────────┐
│  개발자 코드 (rclpy/rclcpp 노드)     Foxglove App        │
│  RoboStack conda env (네이티브)      (네이티브 시각화)     │
│         │                              │ ws:8765        │
│  [zenoh-bridge-ros2dds]        [foxglove_bridge]        │
│         │ tcp:7447 (lima port-forward) │                │
│  ┌─ Lima VM: Ubuntu 22.04 arm64 (Tier 1) ────────────┐  │
│  │  [zenoh-bridge-ros2dds]                           │  │
│  │  Gazebo (headless) ──── move_group (MoveIt)       │  │
│  │  ros-humble-desktop-full (apt 표준 설치)            │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

양측 모두 `ROS_LOCALHOST_ONLY=1`로 DDS를 자기 호스트 안에 가두고,
경계 통과는 오직 zenoh 브리지(TCP 단일 포트)로만 한다.

## 3. 페이즈 개요

| Phase | 이름 | 산출물 | 성공 기준 (Definition of Done) | 상세 문서 |
|---|---|---|---|---|
| 0 | 기술 스파이크 (리스크 킬러) | 검증 리포트 `docs/plan/phase0-results.md` | 3대 가정(RoboStack/VM/브리지) 전부 실측 통과 + go/no-go 결정 기록 | [phase0](docs/plan/phase0-spike.md) |
| 1 | rosmac CLI 코어 | `rosmac init/up/down/status/shell/doctor` 동작 | 맥 셸에서 `ros2 topic echo`로 VM talker 수신 (E2E) | [phase1](docs/plan/phase1-cli-core.md) |
| 2 | 시뮬레이션·시각화 통합 | `rosmac sim <preset>` + Foxglove 자동 연결 | 맥 rclpy 노드 → VM MoveIt 플래닝 → Foxglove 시각화 E2E | [phase2](docs/plan/phase2-sim-viz.md) |
| 3 | (실험) GPU 가속 VM 백엔드 | krunkit/Venus 벤치마크 리포트 | 소프트웨어 렌더링 대비 판정 기준 충족 시 백엔드 채택 | [phase3](docs/plan/phase3-gpu.md) |
| 4 | 제품화 (릴리스 엔지니어링) | 배포 파이프라인, doctor --fix, uninstall, CI | **프레시 macOS 계정**에서 pipx 설치 → 문서만으로 Phase 2 E2E 통과 | [phase4](docs/plan/phase4-productionize.md) |
| 5 | 오픈소스 런칭 | 영어 문서, 데모 자산, 커뮤니티 인프라, v0.1.0 공개 | 제3자가 README만으로 도구의 필요성 이해 + 설치 성공. 공개 행위는 사용자 실행 | [phase5](docs/plan/phase5-launch.md) |
| 6 | 출판 | 벤치마크 스위트, JOSS paper.md, Zenodo DOI | 1차 venue 제출 완료 + 리뷰 대응 체계 | [phase6](docs/plan/phase6-publication.md) |

**순서 규칙**: Phase 0의 게이트를 통과하기 전에는 Phase 1 코드를 쓰지 않는다.
Phase 0에서 아키텍처 가정이 깨지면 이 문서의 2절부터 수정한다.
제품화 트랙은 4 → 5 → 6 순서 강제 (4.6 재현성 게이트 없이 공개 금지,
공개 repo 없이 JOSS 제출 불가). Phase 3(GPU)은 독립 실험 트랙 — 언제든 병행/생략 가능.

## 4. 결정 로그 (Decision Log)

| # | 결정 | 근거 | 재검토 조건 |
|---|---|---|---|
| D1 | ROS2 배포판 = **Humble** | 요구사항 명시. Ubuntu 22.04 arm64 Tier 1 | 사용자가 Jazzy 요구 시 |
| D2 | VM = **Lima** (UTM 아님) | CLI 자동화(YAML 템플릿, provision 스크립트, 포트포워딩, mount)가 압도적으로 쉬움. GUI 불필요(헤드리스 전략) | Phase 3에서 krunkit 채택 시 백엔드 추상화 |
| D3 | 브리지 = **zenoh-bridge-ros2dds** | DDS wire를 zenoh로 변환, TCP 단일 포트, 토픽/서비스/액션 지원 | Phase 0.3 실패 시 → Fast DDS Discovery Server 폴백 |
| D4 | 시각화 1급 = **Foxglove**, RViz2는 보조 | RViz2/OGRE는 macOS에서 구조적으로 불안정(리서치 확인). Foxglove는 macOS 네이티브 앱 | Foxglove 라이선스 정책 변경 시 → Lichtblick(오픈소스 포크) 검토 |
| D5 | CLI 언어 = **Python 3.11+ (typer + rich)** | RoboStack env와 생태계 일치, 배포 pipx/brew 용이, subprocess 오케스트레이션에 충분 | 성능 문제 없음 — 재검토 불필요 |
| D6 | 계획/코드 저장 위치 = `~/workspace/rosmac` | `~/workspace/macros`는 이 프로젝트와 무관한 별도 리포 (다른 remote) — 오염 방지 | — |
| D7 | 맥 네이티브 쪽 ROS2 = RoboStack `robostack-humble` 채널 | osx-arm64 프리빌트 바이너리 제공하는 유일한 채널 | 채널 폐기 시 → 소스빌드 아닌 "맥 네이티브 레이어 포기, VM 단독 모드" |
| D8 | Gazebo 버전 = **Fortress (Ignition)** | Humble의 공식 페어링(`ros-humble-ros-gz`) | Harmonic 조합은 Phase 2에서 별도 검증 항목 |
| D9 | RMW = **rmw_cyclonedds_cpp 양측 통일** (Phase 0 실측, 사용자 승인 2026-07-07) | 기본 fastrtps는 브리지 경유 서비스 요청을 리더 히스토리 프리얼록 버그로 거부 (KI-16). cyclonedds 전환 후 서비스/액션/파라미터 전부 정상 | fastrtps 해당 버그 수정 확인 시 |
| D10 | 배포 채널 = **PyPI + pipx** 1급, Homebrew tap은 후순위 평가만 (사용자 승인 2026-07-07) | 파이썬 CLI의 표준 경로, 자동화 비용 최소 (Trusted Publishing). brew formula는 유지비 대비 이득 불확실 | pipx 설치 마찰이 실측으로 확인될 때 |
| D11 | 공개 문서 = **전부 영어** (한국어 병행판 없음). 내부 계획 문서(docs/plan/)만 한국어 유지 (사용자 승인 2026-07-07) | 도달 범위. 내부 문서 번역은 비용 대비 무가치 | — |
| D12 | 버저닝 = **SemVer**, 공개 시작 v0.1.0, CHANGELOG 유지 (Keep a Changelog) (사용자 승인 2026-07-07) | 0.y 동안 breaking 자유도 확보하면서 사용자 기대 관리 | 1.0 판단 시점에 재검토 |
| D13 | 출판 1차 venue = **JOSS** + ROSCon 병행 — 단 **준비까지만, 제출·발표 신청 등 실행은 보류** (사용자 결정 2026-07-07) | 기여의 본질이 엔지니어링 통합+실측 함정 DB — JOSS와 일치. 실행 시점은 사용자가 별도 지시 | 사용자가 제출 지시할 때 실행 단계 활성화 |

## 5. 리스크 레지스터

| # | 리스크 | 영향 | 확률 | 완화책 | 감지 시점 |
|---|---|---|---|---|---|
| R1 | ~~zenoh 브리지가 MoveIt **액션** QoS를 제대로 매핑 못 함~~ **해소** (Phase 0.3 실측: T5 accepted+feedback 스트림+SUCCEEDED, transient_local 포함) | — | — | D9(cyclonedds 통일) 유지가 전제 — fastrtps로 되돌리면 재발 (KI-16) | 해소됨 2026-07-07 |
| R2 | RoboStack 패키징 버그 (예: dylib 링크 깨짐 — ros-noetic#459에서 libprotobuf 사례 확인됨) | 중 (개발 루프 저하) | 중 | `rosmac doctor`에 지문 감지 내장, 버전 핀 목록 유지 | Phase 0.1, 상시 |
| R3 | ~~Lima VM Gazebo 물리 성능 부족~~ **해소** (P2.4 실측: 소프트웨어 EGL로 RTF 0.99, 카메라 15Hz 만속) | — | — | 고해상도/복수 센서는 Phase 3에서 재평가 | 해소됨 2026-07-07 |
| R4 | ~~대용량 토픽 브리지 병목~~ **해소** (P0.3: 10.3MB/s, P2.4: 카메라 zenoh 경유 무손실 14.4fps) | — | — | 더 큰 이미지가 필요하면 Foxglove 8765 직결 경로 사용 (이미 기본) | 해소됨 2026-07-07 |
| R5 | macOS 업데이트로 Lima/가상화 프레임워크 동작 변경 | 저 | 저 | CI 없음(개인 도구) → doctor가 버전 매트릭스 경고 | 상시 |
| R6 | 브리지 이중 실행/좀비 프로세스로 토픽 루프·중복 | 중 | **고 (실측 확인)** | pidfile + `rosmac up` 멱등성 설계 (Phase 1.5). Phase 0 실측: SIGKILL 후 재기동 시 상대 브리지의 라우트 잔재로 정확히 2배 수신 (KI-17) → **SIGTERM 정상 종료 필수** | Phase 1 |
| R7 | 업스트림 드리프트 — RoboStack 채널/zenoh 릴리스/lima 변경으로 **신규 설치**가 깨짐 (기존 사용자는 핀으로 보호되나 신규 유입이 죽음) | 고 (공개 후 신뢰 직결) | 중 | weekly CI가 실제 env 생성·URL 검증 (P4.4), 실패 시 자동 이슈. 버전 핀 + doctor 매트릭스 | Phase 4부터 상시 |
| R8 | 단일 메인테이너 부하 — 공개 후 이슈/PR 대응이 지속 불가능해짐 | 중 | 중 | 지원 범위 명문화(비목표 절), `rosmac report`로 이슈 품질 강제, 함정 DB 기여 구조로 커뮤니티 분담 | Phase 5 런칭 후 |
| R9 | 이름·상표 — PyPI `rosmac` 선점, "ROS" 상표 정책(Open Robotics) 저촉 | 저 | 저 | P4.5에서 이름 확보 선행, P5.5에서 상표 정책 확인·기록. 비상업·비접두(ros-*) 이름이라 위험 낮음 | Phase 4.5 |
| R10 | 공개 이력 리스크 — git 이력의 민감정보(경로, 이메일, 내부 메모) | 중 | 저 | P5.5 점검 체크리스트에 이력 전수 스캔 포함. 발견 시 공개 전 처리 (필요시 squash 재구성 — 사용자 결정) | Phase 5.5 |

## 6. 리포지토리 구조 (Phase 1에서 생성)

```
rosmac/
├── PLAN.md                     # 이 문서
├── docs/plan/                  # 페이즈별 상세 계획 + 결과 리포트
├── pyproject.toml
├── src/rosmac/
│   ├── cli.py                  # typer 엔트리포인트
│   ├── config.py               # ~/.rosmac/config.yaml 로드/검증
│   ├── lima.py                 # limactl 래퍼
│   ├── conda.py                # micromamba 래퍼
│   ├── bridge.py               # zenoh 브리지 프로세스 관리
│   ├── doctor.py               # 진단
│   ├── sim.py                  # (Phase 2) 프리셋 실행
│   └── assets/
│       ├── lima/rosmac.yaml    # Lima VM 템플릿
│       ├── provision/          # VM 프로비저닝 셸 스크립트
│       ├── presets/            # (Phase 2) 시뮬 프리셋 YAML
│       └── layouts/            # (Phase 2) Foxglove 레이아웃 JSON
└── tests/
    ├── unit/
    └── e2e/                    # 실제 VM 필요, 수동/태그 실행
```

## 7. 작업 규약

- 커밋 단위: 계획서의 태스크 번호(예: `[P1.4] rosmac init: RoboStack env 생성`).
- 각 태스크는 상세 문서의 **완료 기준(AC)** 을 전부 만족해야 완료로 표기.
- 검증 명령의 실제 출력은 `docs/plan/phaseN-results.md`에 붙여넣어 기록 (버전 번호 포함 — 재현성).
- 상세 문서의 명령어는 "계획 시점 최선"이며, 실행 중 달라지면 문서를 고치고 결과 리포트에 사유를 남긴다.

# AGENTS.md — rosmac 실행 에이전트 가이드

> 이 문서는 **계획을 수립한 에이전트(Fable)가 아닌 다른 에이전트/모델**(Opus, Sonnet,
> Codex, 사람 포함)이 계획을 이어받아 수행할 수 있도록, 대화에만 있고 문서에 없던
> 배경지식과 작업 규칙을 명문화한 것이다.
> **어떤 태스크든 시작 전에 이 문서 전체를 먼저 읽는다.**

---

## 1. 이 프로젝트가 존재하는 이유 (배경지식 — 외부 검색 불필요)

ROS2 Humble은 macOS를 사실상 지원하지 않는다. 2026-07-07 딥리서치로 검증된 사실:

- ROS2의 플랫폼 지원은 **"OS + CPU 아키텍처" 조합** 단위다 (REP-2000).
  Ubuntu 22.04 arm64 = **Tier 1**(바이너리 + CI 완전 지원) ↔ macOS = Tier 3
  (Intel 소스빌드만, Apple Silicon은 목록에 아예 없음). **Jetson/Orin이 잘 되는 이유는
  arm64여서가 아니라 Ubuntu여서다.** 따라서 "arm 빌드 타겟만 추가하면 되지 않나"는
  틀린 접근이다 — 장벽은 SIP(DYLD 환경변수 차단), Homebrew 의존성 지옥,
  OGRE/OpenGL 그래픽 스택 등 전부 OS 레벨이다.
- RViz2의 macOS 실패는 Intel Mac에서도 재현된다 (ros2/rviz#929) → arm 문제 아님.
  그래서 이 프로젝트는 RViz2가 아닌 **Foxglove**를 1급 시각화 도구로 쓴다.
- **RoboStack**(conda 채널)만이 osx-arm64용 ROS2 Humble 프리빌트 바이너리를 제공한다.
  단 커뮤니티 패키징이라 dylib 링크 깨짐 같은 버그가 간헐적으로 있다.
- DDS(ROS2의 통신층)는 멀티캐스트 디스커버리를 쓰는데 **VM NAT 경계를 넘지 못한다.**
  이것이 "맥 네이티브 + VM" 하이브리드를 시도한 사람들이 전부 막힌 지점이고,
  이 프로젝트가 zenoh-bridge-ros2dds로 푸는 핵심 문제다.

이 프로젝트(rosmac)는 위 제약을 **레이어 분리**로 우회한다:
개발(맥 네이티브 RoboStack) / 시뮬레이션·MoveIt(Lima VM의 Ubuntu 22.04 arm64) /
시각화(맥 Foxglove) / 경계 연결(zenoh 브리지). 상세는 `PLAN.md` 2절.

## 2. 문서 지도와 읽는 순서

| 순서 | 문서 | 용도 |
|---|---|---|
| 1 | `AGENTS.md` (이 문서) | 작업 규칙, 배경, 용어 |
| 2 | `PLAN.md` | 아키텍처, 페이즈 개요, **결정 로그(D1~D8)**, **리스크(R1~R6)** |
| 3 | `docs/plan/phaseN-*.md` | 지금 수행할 태스크의 상세 절차 |
| 4 | `docs/plan/known-issues.md` | 막혔을 때 **가장 먼저** 볼 함정 DB |
| 5 | `docs/plan/phaseN-results.md` | 선행 태스크의 실측 결과 (존재하면 반드시 읽기 — 버전 핀, 확정된 채널명 등이 여기 있음) |

## 3. 절대 규칙 (위반 금지 — 이유 불문)

1. **`csrutil disable`(SIP 비활성화) 금지.** 어떤 에러가 나와도 SIP를 끄는 해법은
   채택하지 않는다. SIP 없이 안 되는 경로면 그 경로 자체를 기각한다 (아키텍처 전제).
2. **사용자 글로벌 환경을 임의로 바꾸지 않는다.** `~/.zshrc` 수정, 시스템 Python 변경,
   brew 패키지 임의 설치 금지. 설치가 필요하면 명령을 출력하고 사용자 확인을 받거나,
   문서에 명시된 것(`brew install lima/micromamba` 등)만 실행한다.
3. **결정 로그(D1~D8) 변경은 사용자 승인 필요.** "Lima 대신 Docker가 낫겠다" 같은
   아키텍처 변경을 임의로 하지 않는다. 근거를 정리해 사용자에게 묻고, 승인되면
   PLAN.md의 결정 로그를 갱신한 뒤 진행한다.
4. **완료 기준(AC) 체크박스를 건너뛰지 않는다.** 검증 없이 "될 것이다"로 완료 표기 금지.
   각 AC는 실제 명령 실행 + 출력 확인으로만 체크한다.
5. **버전을 핀하고 기록한다.** 다운로드하는 모든 바이너리/패키지의 버전과 (가능하면)
   sha256을 `phaseN-results.md`에 남긴다. "latest"를 코드에 하드코딩하지 않는다.
6. **실험 파일은 `~/rosmac_spike/`, 코드는 `~/workspace/rosmac/`에만** 만든다.
   `~/workspace/macros`는 이 프로젝트와 무관한 과제 리포다 — 건드리지 않는다 (D6).
7. **파괴적 명령 주의**: `limactl delete`는 문서가 명시한 지점에서만.
   `rm -rf`, `micromamba env remove`는 대상 경로를 출력·확인 후 실행.
8. 계획 문서와 현실이 다르면 **현실을 따르되 문서를 고친다** — 절차를 수정 실행했으면
   해당 phase 문서를 편집하고, 사유를 `phaseN-results.md`에 남긴다. (규약: PLAN.md 7절)

## 4. 태스크 수행 프로토콜

모든 태스크(P0.1, P1.4 등)는 이 루프로 수행한다:

```
1. 해당 phase 문서에서 태스크 섹션 전체를 읽는다 (목적/선행조건/절차/AC/실패 대응).
2. 선행 조건 확인 — 미충족이면 선행 태스크부터. 선행 결과는 phaseN-results.md에서 조회.
3. 절차를 순서대로 실행. 각 명령의 실제 출력을 기대 출력(부록 A)과 대조.
4. 명령 실패 시:
   a. known-issues.md에서 에러 메시지 검색 → 있으면 처방 적용
   b. 없으면 해당 태스크의 "실패 시 대응" 절 적용
   c. 그래도 실패 → 최대 2회 변형 재시도 후 중단, 아래 5.의 에스컬레이션
5. AC 전 항목 체크 → phaseN-results.md에 기록 (템플릿: docs/plan/templates/) →
   커밋: git commit -m "[PX.Y] <한 줄 요약>"
6. 새로 발견한 함정은 known-issues.md에 추가 (증상/원인/해결 형식).
```

### 에스컬레이션 기준 (사용자에게 물어야 하는 경우)
- 결정 로그 D1~D8을 바꿔야만 진행 가능할 때
- Phase 0의 게이트 판정 (GO / GO-수정 / NO-GO)
- 문서에 없는 유료 서비스 가입, 계정 생성이 필요할 때
- 같은 태스크에서 서로 다른 접근 2회가 모두 실패했을 때
  → 시도한 것/에러 전문/다음 가설을 정리해서 보고

### 에스컬레이션이 아닌 것 (스스로 결정)
- 만료된 다운로드 URL을 현행 URL로 교체 (기록만 남기면 됨)
- 문서의 명령 오타/경로 수정
- 타임아웃 값, 재시도 횟수 같은 전술적 파라미터 조정

## 5. 검증 철학

- "창이 떴다"가 아니라 **구체 신호**로 판정한다: 토픽 수신은 `ros2 topic echo --once`의
  exit 0 + 페이로드, 프로세스 생존은 pid 존재 + 5초 후 재확인, 서비스는 응답값 대조.
- 성능 수치(RTF, fps, 대역폭)는 **3회 측정 중앙값**을 기록한다.
- E2E 테스트는 반드시 **깨끗한 상태에서** 시작한다 (문서에 초기화 절차 명시됨).
- 육안 확인이 필요한 항목(Foxglove 렌더링)은 스크린샷을 `docs/plan/evidence/`에 저장.

## 6. 다른 에이전트에게 태스크를 넘길 때 (사람용 프롬프트 템플릿)

```
프로젝트: ~/workspace/rosmac
1. AGENTS.md 전체를 읽고 규칙을 따르세요.
2. PLAN.md와 docs/plan/<phase 문서>를 읽으세요.
3. 태스크 <PX.Y>만 수행하세요. 스코프 밖 작업 금지.
4. 완료 기준(AC)을 전부 실측으로 체크하고 docs/plan/phaseN-results.md에 기록하세요.
5. 막히면 known-issues.md 확인 → 실패 대응 절 → 그래도 안 되면 중단하고 보고하세요.
```

## 7. 용어집 (이 프로젝트 문서를 읽는 데 필요한 최소 지식)

| 용어 | 뜻 (이 프로젝트 맥락) |
|---|---|
| **ROS2 Humble** | 로봇 미들웨어 ROS2의 LTS 배포판 (2022). Ubuntu 22.04와 페어링 |
| **DDS / RMW** | ROS2의 통신 계층 / 그 구현 선택 변수(`RMW_IMPLEMENTATION`). 기본 fastrtps, 대안 cyclonedds. **양측이 달라도 DDS 표준상 통신은 되지만, 문제 분리를 위해 통일해서 테스트** |
| **QoS / transient_local** | 토픽 전달 보장 설정. transient_local = 늦게 구독해도 마지막 값 수신(latched). `/robot_description`이 이 패턴 — 브리지가 이걸 보존 못 하면 Foxglove가 로봇 모델을 못 받음 |
| **ROS_LOCALHOST_ONLY=1** | DDS 트래픽을 자기 호스트로 제한. 이 프로젝트에선 **양측 필수** — 경계 통과는 zenoh 브리지만 담당하게 만드는 격리 장치 |
| **ROS_DOMAIN_ID** | DDS 논리 네트워크 ID. 양측 동일해야 브리지가 매핑 (기본 0) |
| **zenoh-bridge-ros2dds** | Eclipse zenoh 프로젝트의 DDS↔zenoh 브리지. 각 호스트의 로컬 DDS를 zenoh 프로토콜(TCP 단일 포트)로 상호 연결. 토픽/서비스/액션 지원이 공식 스펙이나 **액션 실측이 Phase 0.3의 핵심** |
| **RoboStack** | ROS를 conda 패키지로 재빌드해 배포하는 커뮤니티 프로젝트. osx-arm64 지원. 채널명이 `robostack-humble`인지 `robostack-staging`인지 설치 시점에 확인 필요 (Phase 0.1) |
| **micromamba** | conda 호환 경량 패키지 매니저. RoboStack 설치에 사용 |
| **Lima** | macOS용 Linux VM 매니저 (CLI, YAML 템플릿, 자동 포트포워딩). `limactl` 명령 |
| **colcon** | ROS2 표준 빌드 도구 (`colcon build`, `source install/setup.zsh`) |
| **MoveIt / move_group** | 로봇 팔 모션플래닝 프레임워크 / 그 중앙 노드. 통신이 **액션**(`/move_action`, goal→feedback 스트림→result) 중심이라 브리지의 액션 지원이 필수 |
| **Gazebo Fortress** | Humble과 페어링되는 시뮬레이터 (구명 Ignition, 명령어 `ign gazebo`). `-s` = 헤드리스 서버만. Gazebo "Classic"(11)과는 다른 소프트웨어 |
| **ros_gz_bridge** | Gazebo 내부 토픽 ↔ ROS2 토픽 변환기 (zenoh 브리지와 별개, VM 내부용) |
| **Foxglove / foxglove_bridge** | 로봇 데이터 시각화 앱(macOS 네이티브) / ROS2를 websocket(8765)으로 노출하는 서버 노드. **VM 쪽에서 실행** (설계 근거: phase2 2.1) |
| **RTF** | Real Time Factor — 시뮬 시간/실제 시간 비. 1.0 = 실시간 |
| **SIP** | macOS System Integrity Protection. 끄지 않는다 (절대 규칙 1) |
| **Tier 1/3, REP-2000** | ROS2 공식 플랫폼 지원 등급 문서. 1절 참조 |

## 8. 실행 환경 사실

- 호스트: Apple Silicon Mac, macOS (Darwin 25.x), 기본 셸 zsh
- 이 리포: `~/workspace/rosmac` (git). 과제 리포 `~/workspace/macros`와 무관
- 네트워크 포트 예약: 7447(zenoh), 8765(foxglove), 11811(폴백 시 discovery server)
- 상태 디렉토리(Phase 1부터): `~/.rosmac/` — config.yaml, bin/, run/, log/

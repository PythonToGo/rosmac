# Phase 0 결과 리포트 — 2026-07-07

> 진행 중 문서 — 태스크 완료 시마다 갱신.

## 0. 실행 환경
- macOS 버전 / 칩 / RAM: macOS 26.5.2 (Darwin 25.5.0) / Apple M3 Pro / 18GB
- 실행 에이전트(모델명) 및 날짜: Claude Fable 5 (claude-fable-5), 2026-07-07
- 도구 버전: lima=2.1.4 / micromamba=2.8.1 / zenoh-bridge=1.9.0 / python(ros_env)=3.12.13
- Homebrew 6.0.5 (micromamba·lima는 이번에 `brew install`로 설치 — AGENTS.md 규칙 2의 허용 목록)

## 태스크별 기록

### P0.1 RoboStack Humble osx-arm64 스모크 테스트 — PASS
- 완료 기준(AC) 체크리스트:
  - [x] talker↔listener 메시지 교환 확인 ("I heard" 연속 수신, 부록 A1 충족)
  - [x] rviz2가 뜨고 1분 이상 크래시 없음 (84초 생존 확인, Grid 렌더링 31fps, 에러 로그 0건)
  - [x] `colcon build` + `source install/setup.zsh` 성공 (spike_py_node, 1.13s)
  - [x] `ros-humble-moveit`(2.5.9 `_18` — 현 env와 단독 설치 가능),
        `ros-humble-foxglove-bridge`(0.8.5 `_13`까지만 존재 — 현 env와 비호환, KI-14) 확인
  - [x] SIP 비활성화 없이 전부 동작 (csrutil 안 건드림)
- 확정/핀한 것:
  - 채널명: **`robostack-humble`** (robostack.github.io/GettingStarted.html 2026-07-07 확인)
  - `ros-humble-desktop 0.10.0 np2py312h50b1e4c_18`, `ros2-distro-mutex 0.9.0 humble_18`,
    `python 3.12.13`, `ros-humble-rmw-fastrtps-cpp 6.2.10 _18`
  - env 생성 명령: `micromamba create -n ros_env -c conda-forge -c robostack-humble
    ros-humble-desktop compilers cmake pkg-config make ninja colcon-common-extensions rosdep`
- 계획 문서와 다르게 수행한 것 + 사유:
  - `micromamba shell init -s zsh` 미실행 — `~/.zshrc` 수정은 절대 규칙 2(글로벌 환경 변경 금지)
    위반이라 `MAMBA_ROOT_PREFIX=~/micromamba` + `eval "$(micromamba shell hook -s zsh)"` 방식으로 대체.
    사용자가 대화형으로 쓰려면 shell init을 직접 실행하면 됨
  - dry-run에서 moveit+foxglove-bridge 동시 설치는 실패 → 원인 분석 후 KI-14로 기록.
    **moveit 단독은 정상 솔브** (아키텍처상 맥 쪽 foxglove-bridge는 불필요 — phase2 2.1)
- 발견한 함정: KI-14 (foxglove-bridge 빌드 세대), KI-15 (micromamba run 락 경합)
- 사소한 경고: env 링크 중 `gdk-pixbuf loaders.cache already present` 경고 1건 (기능 영향 없음),
  zsh에서 `compdef:153: _comps: assignment to invalid subscript range` 경고 (KI-9 유형, 동작 무관)
- 증거: `docs/plan/evidence/p0.1-rviz2.png` (Grid 렌더링, "RViz is ready", 31fps)

### P0.2 Lima VM + apt ROS2 Humble 설치 — PASS
- 완료 기준(AC) 체크리스트:
  - [x] provision 스크립트만으로 무인 설치 완료 — 1차 시도는 KI-13으로 실패,
        OSRF 저장소 추가 후 성공 (아래 수정 내역)
  - [x] VM 내부 talker/listener 동작 (`topic hz` 0.999Hz; 재생성 VM에서
        `ros2 topic echo --once /chatter` exit 0 + 페이로드)
  - [x] 호스트→VM 포트포워딩(7447) 확인 (1차·재생성 VM 모두 curl HTTP 200)
  - [x] 삭제 후 재생성이 무인으로 재현됨 (`limactl delete -f` → `limactl start`,
        개입 0회, provision 실패 0건, ROS 패키지 322개 동일)
  - [x] 기록: 재프로비저닝 소요 **162초**(이미지 캐시 상태), 디스크 6.9GB/30GB, lima 2.1.4
- 확정/핀한 것:
  - 이미지: `https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-arm64.img`
  - VM ROS: `ros-humble-desktop-full 0.10.0-1jammy.20260613.005307` (+ ros-dev-tools), ROS 패키지 322개
  - `ros2 doctor`: "All 5 checks passed" (부록 A2 충족)
  - 디스크 사용량(설치 후): 6.9GB / 30GB
  - **provision 필수 수정**: OSRF gazebo-stable 저장소 추가 (KI-13) — lima-rosmac.yaml,
    phase0-spike.md 모두 반영 완료
- 발견한 함정: KI-13 (libignition-sensors6 6.8.1 의존성 — packages.ros.org만으로 불충족)
- 에러 전문(1차 provision 실패):
  ```
  Depends: libignition-sensors6-camera (>= 6.8.1) but 6.8.0-1~jammy is to be installed
  ...
  E: Unable to correct problems, you have held broken packages.
  LIMA ... WARNING: Failed to execute /mnt/lima-cidata/provision.system/00000000
  ```
  주의: 이 실패에도 `limactl start`는 exit 0 + READY를 반환함 — provision 실패가
  기동 성공으로 위장될 수 있으니 Phase 1 `rosmac init`은 `/opt/ros/humble/setup.bash`
  존재를 반드시 후검증할 것
- 계획 문서와 다르게 수행한 것 + 사유: provision 스크립트에 OSRF gazebo-stable
  저장소 추가 (KI-13 — 문서 수정 완료: phase0-spike.md, ~/rosmac_spike/lima-rosmac.yaml).
  1차 VM은 수동으로 저장소 추가 후 설치해 검증했고, 최종 판정은 수정 YAML로
  delete→재생성한 2차 VM에서 수행

### P0.3 zenoh-bridge-ros2dds 왕복 검증 — PASS (T1~T9 전항목 + transient_local)
- 바이너리 (양측 동일 버전 **1.9.0**, standalone, `-l`/`-e` 플래그 유효 확인):
  - mac(aarch64-apple-darwin): sha256 `997415721cfbb74b209b9968e7a7e4f6bed94e6afa4559ddb02ee1b2edccc899`
  - linux(aarch64-unknown-linux-gnu): sha256 `e3eb1fd4459e4b877653419b1c25eaf92418d70fe53ee767eca005f1a19443dc`
- **RMW 조합: 양측 `rmw_cyclonedds_cpp` 1.3.4로 통일** (기본 fastrtps는 서비스에서
  KI-16 발생 → 폴백 사다리 1단계 적용, 문서에 예고된 경로). 브리지 기동 env:
  `ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=0 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`
  + 맥 쪽은 `ROS_DISTRO=humble` 명시 필요 (없으면 브리지가 'iron' 가정 경고)

| 테스트 | 결과 | 수치/비고 |
|---|---|---|
| T1 토픽 VM→맥 | **PASS** | echo exit 0 + 페이로드, hz 0.999 (≈1Hz) |
| T2 토픽 맥→VM | **PASS** | echo exit 0, hz 0.997. 디스커버리 전파 ~10s 지연 관찰 |
| T3 토픽 목록 가시성 | **PASS** | 양방향 모두 상대 토픽 표시 |
| T4 서비스 | **PASS** | sum=42 정상 반환 (fastrtps에서는 KI-16으로 실패 → cyclonedds로 해결) |
| T5 **액션** | **PASS** | goal accepted + **feedback 3회 스트림** + result + SUCCEEDED (A5 3요소 전부) |
| T6 파라미터 | **PASS** | `param list`/`get /talker use_sim_time` → False |
| T7 대역폭 | **PASS** | 3회 측정: 10.33 / 10.21 / 11.13 MB/s → **중앙값 10.33 MB/s** (기준 5MB/s), 1MB@10Hz 드랍 없음 |
| T8 안정성 10분 | **PASS** | 동일 PID 15분+ 생존, RSS 맥 15.4→13.5MB / VM 18.9→19.4MB (폭주 없음), hz 1.000 유지 |
| T9 재연결 | **PASS** | 맥 브리지 SIGTERM→재기동 후 수동 개입 없이 재개 (hz 1.001, 중복 없음). ⚠️ SIGKILL 시에는 KI-17 (2배 수신) — 정상 종료 필수 |
| transient_local | **PASS** | latched `/desc`를 발행 후 **진짜 늦은 구독** 2회 모두 수신 (구독측 QoS 명시 필요 — KI-7 ③) |

- 발견한 함정: KI-16 (fastrtps 서비스 무응답), KI-17 (브리지 비정상 종료 잔재 → 토픽 2배),
  KI-18 (pkill 자기 매칭)
- 관찰 사항 (Phase 1 설계 입력):
  - 맥 브리지는 Router 모드로 [::]:7447도 listen — lima 포워드(127.0.0.1:7447, IPv4)와
    충돌은 없지만, Phase 1에서는 명시 설정으로 listen을 끄거나 포트를 분리 권고
  - `limactl start`는 provision 실패해도 exit 0 → 후검증 필수 (P0.2 기록 참조)
  - ros2 데몬이 가끔 죽은 상태로 남음 → `ros2 daemon stop` 후 재시도로 해결

## 게이트 결정 — **GO 확정 (사용자 승인 2026-07-07, D9 포함)**
- 판정: **GO** (아키텍처 수정 없음, 전술적 확정 사항 3건 포함)
- PLAN.md 반영 완료: D9 추가, R1 해소 표기, R6 확률 상향+근거 보강, 상태줄 갱신
- 판정 근거:
  - 3대 가정 전부 실측 통과: RoboStack 맥 네이티브(P0.1 PASS), Lima VM 무인 프로비저닝
    (P0.2 PASS, 재현성 포함), zenoh 브리지 T1~T9 + transient_local (P0.3 PASS)
  - 최대 리스크였던 T5 액션은 feedback 스트림 포함 완전 통과 → R1 해소
  - 폴백 사다리는 1단계(RMW cyclonedds 통일)까지만 사용 — 문서에 예고된 경로
- PLAN.md 반영 제안 (승인 필요):
  1. **신규 결정 D9**: 양측 RMW 기본값 = `rmw_cyclonedds_cpp` (근거: KI-16 —
     fastrtps는 브리지 경유 서비스가 구조적으로 깨짐. 재검토 조건: fastrtps 버그 수정 확인 시)
  2. R1 상태 갱신: "해소 (Phase 0 실측)" — 완화책을 "cyclonedds 통일 유지"로 교체
  3. R6 근거 보강: KI-17 (브리지 비정상 종료 시 라우트 잔재 → 2배 수신) —
     `rosmac up/down`의 pidfile + SIGTERM 정상 종료가 필수임이 실측으로 확인됨

## 다음 페이즈 인계 메모
- 스파이크 VM(`rosmac-spike`)은 정지 상태로 보존 (`limactl start rosmac-spike`로 재개).
  Phase 1 자산의 원형은 `~/rosmac_spike/lima-rosmac.yaml` (OSRF 저장소 포함 버전)
- 맥 브리지 기동 시 env 4개 필수: `ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=0
  RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DISTRO=humble` (마지막 것 빠지면 iron 가정)
- `limactl start`는 provision 실패해도 exit 0 → `rosmac init`은 `/opt/ros/humble/setup.bash`
  존재를 후검증할 것. 브리지 종료는 반드시 SIGTERM (KI-17)

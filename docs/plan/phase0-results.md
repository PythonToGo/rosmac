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

### P0.3 zenoh-bridge-ros2dds 왕복 검증 — 착수 전
- 바이너리 확보 완료 (양측 동일 버전 **1.9.0**, standalone):
  - mac(aarch64-apple-darwin): sha256 `997415721cfbb74b209b9968e7a7e4f6bed94e6afa4559ddb02ee1b2edccc899`
  - linux(aarch64-unknown-linux-gnu): sha256 `e3eb1fd4459e4b877653419b1c25eaf92418d70fe53ee767eca005f1a19443dc`

## 게이트 결정
- (0.1~0.3 완료 후 기입)

## 다음 페이즈 인계 메모
- (게이트 통과 후 기입)

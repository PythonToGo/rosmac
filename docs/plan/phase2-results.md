# Phase 2 결과 리포트 — 2026-07-07

## 0. 실행 환경
- Phase 0/1과 동일 (macOS 26.5.2 / M3 Pro / 18GB, lima 2.1.4, micromamba 2.8.1)
- 실행 에이전트: Claude Fable 5, 2026-07-07
- 추가 버전: ros-humble-foxglove-bridge 3.4.2, ros-humble-moveit 2.5.x(apt VM),
  ros-humble-ros-gz(Fortress, ign 6.18.0), Foxglove 앱(맥, 설치돼 있었음)

## 태스크별 기록

### P2.1 foxglove_bridge 자동화 — PASS
- AC: [x] `rosmac viz` → Foxglove 연결 + VM /chatter 확인
  (앱 연결 스크린샷 + **웹소켓 프로토콜 레벨 검증**: advertise 채널에 /chatter 포함)
  [x] `/robot_description` → 3D 패널 URDF 로드 (P2.3에서 Panda로 실증 —
  evidence/phase2-panda-ready.png)
- 구현: 30-foxglove.sh (systemd, 기본 disabled — up --viz/sim에서 start),
  `rosmac viz` 딥링크 (`foxglove://open?ds=foxglove-websocket&ds.url=…` 동작 확인)
- 발견한 함정: KI-21 — foxglove_bridge 3.4.x는 Rust SDK 서버로 재작성돼 웹소켓
  서브프로토콜이 `foxglove.sdk.v1` (구 `foxglove.websocket.v1` 클라이언트는 HTTP 400).
  systemd 유닛에 HOME 필수 (없으면 rcl_logging 크래시)

### P2.2 프리셋 시스템 (rosmac sim) — PASS
- AC: [x] 미존재 프리셋 → 목록 출력 (exit 1) [x] 이중 실행 → 기존 세션 안내 (exit 1)
  [x] health 타임아웃 → tmux 로그 30줄 + exit 1 (더미 프리셋으로 3종 실측)
- 구현: 선언적 YAML(패키지 assets + ~/.rosmac/presets 사용자 오버라이드),
  tmux 세션, health_topics 폴링(맥 시점 — 브리지 경유까지 한 번에 검증됨),
  프리셋 자산 디렉토리 push (assets/presets/<name>/ → VM ~/rosmac-presets/<name>/)
- 보강(P2.4 실측 후): stop이 tmux kill 후 고아 gz/bridge도 pkill — tmux kill 시점에
  launch가 시그널 핸들러 등록 전이면 자식이 살아남아 토픽 2배/기아 유발

### P2.3 panda-moveit — PASS
- 사전 검증: 후보 1(`moveit_resources_panda_moveit_config`의 demo.launch.py)은
  **존재하지만 rviz를 끌 수 없음** (rviz_tutorial 인자는 rviz config 선택일 뿐) +
  ros2_control 미설치 의존 → **rviz/db만 제거한 headless launch를 동봉**으로 확정
  (부록 C 패턴, 구성 파라미터는 상류와 동일)
- AC: [x] READY 무인 도달 (health: /joint_states, /monitored_planning_scene)
  [x] 맥 → `/move_action` goal → **3/3 SUCCEEDED** (ready→extended→ready,
  error_code=1) — 브리지 경유 액션 실전 검증 완료
  [x] Foxglove 3D 팔 자세 변화 (evidence/phase2-panda-ready.png, -extended.png)
- SRDF 실측: group_states ready/extended/transport, 그룹명 panda_arm (부록 A와 일치)
- 발견한 함정:
  - KI-22: setuptools 신버전이 실행 파일을 bin/에 설치 → ros2 run 못 찾음 → setup.cfg
  - KI-23 (**중요**): CycloneDDS 참가자 인덱스 기본 10개 제한 (lo 유니캐스트 디스커버리)
    → spawner 죽음 → goal이 CONTROL_FAILED(-4) 즉시 반환. cyclonedds.xml로 120 확장,
    모든 실행 경로(systemd/run_in_env/bridge/shell/sim)에 CYCLONEDDS_URI 주입

### P2.4 gazebo-diffbot — PASS
- 확정 구성: 동봉 월드 `diffbot_camera.sdf` (diff_drive.sdf + sensors 시스템(ogre2) +
  vehicle_blue 전방 카메라 320x240@15Hz), `ign gazebo -s --headless-rendering`
  - 기본 ogre 엔진은 X11 필수라 헤드리스에서 크래시 ("Unable to open display") →
    ogre2 + EGL로 해결 (Phase 3 GPU 백엔드 없이도 소프트웨어 EGL로 동작)
  - ros_gz_bridge는 **단방향**(`[`/`]`)으로 — `@`(양방향)는 GZ→ROS 출력이 ROS→GZ로 되먹임
- AC: [x] READY 무인 도달 [x] 맥 /cmd_vel(0.5m/s)로 주행, /odom x: 2.40→5.40
  (6초, 물리와 정확히 일치) [x] Foxglove: /camera 이미지 렌더 확인
  (evidence/phase2-diffbot-foxglove.png), odom은 데이터 도달 확인 (시각화는 diffbot 레이아웃)
- 측정값 (3회 중앙값, R3/R4 데이터):
  | 항목 | 값 |
  |---|---|
  | RTF 물리만 | **0.9987** |
  | RTF 카메라 on | **0.9878** (기준 0.5의 2배 — 저해상도 조정 불필요) |
  | /camera fps VM 로컬 | 14.4 (정격 15) |
  | /camera fps 맥 (zenoh 경유) | **14.4 — 무손실** (~3.5MB/s) |

### P2.5 Foxglove 레이아웃 — PASS (결정 기록 포함)
- panda.json (3D+RawMessages+Log), diffbot.json (3D odom+Image+Plot) 작성, JSON 검증
- **결정**: Foxglove 딥링크/CLI는 로컬 레이아웃 파일 지정 미지원 →
  `rosmac viz --layout <name>`이 ~/.rosmac/layouts/에 스테이징 + Import 안내 출력
  (문서 2.5가 예정한 대체 경로). 최초 1회 수동 import 필요 — 새 설치 재현 검증은
  사용자 확인 항목으로 남김

### P2.6 pick_demo + workflow 문서 — PASS
- examples/pick_demo (rclpy MoveGroup 클라이언트, named target 순회) — 맥 colcon
  빌드 → VM MoveIt 구동 실증 (P2.3에서 3/3)
- docs/workflow.md: 데이터 경로 다이어그램, 개발 루프, 함정표(doctor/KI 상호 링크)

### P2.7 E2E + README — PASS
- AC: [x] 시나리오 무인 통과 (`tests/e2e/test_phase2.sh`): up --viz → sim panda-moveit
  READY → 맥 colcon 빌드 → **pick_demo 3/3 SUCCEEDED** → sim stop + down 잔여 0.
  최종 실행 **25초** (웜 상태; 콜드 부팅 포함 시 sim READY까지 +40s 내외)
  [x] 이 리포트 [x] README.md (Quickstart/커맨드/실측 성능)
- 디버깅 여정 (4회 실패 → 통과):
  1. wait_for_server 20s < 액션 라우트(서비스 5종) 전파 → 60s 상향
  2. VM 콜드 부팅 시 /joint_states가 health 30s 데드라인을 초과 → 90s로 보정
  3~4. **KI-23 변형 발견 (핵심)**: VM 재부팅 후 zenoh-bridge systemd 유닛에
  CYCLONEDDS_URI가 누락돼 있었음 — Max=9인 브리지는 참가자 인덱스 10+를 영원히
  발견 못 해 "토픽 일부 OK, 서비스/액션 무응답, 시점 따라 오락가락"이라는 최악의
  부분 가시성 장애 발생. 유닛 수정 + KI-23에 점검법 추가. **모든 DDS 프로세스가
  동일한 CycloneDDS 설정을 가져야 한다**가 이 아키텍처의 불변 조건임을 확인

## 다음 페이즈 인계 메모 (Phase 3 실행자에게)
- v0.1 릴리스 가능 상태: init→up→sim→viz→개발 루프 전부 무인 동작, README 완비
- Phase 3(GPU/krunkit) 착수 전 확인: 현 소프트웨어 EGL 렌더링이 이미 RTF 0.99를
  내므로, Phase 3의 가치는 고해상도 카메라/복수 센서 시나리오에서 측정할 것
- 신규 노드가 서비스/액션만 안 보이면 무조건 KI-23 변형부터 점검
  (`/proc/<pid>/environ`에 CYCLONEDDS_URI 확인)
- Foxglove 레이아웃 import는 최초 1회 수동 (rosmac viz --layout이 안내)

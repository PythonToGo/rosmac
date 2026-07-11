# E.17 Nav2 프리셋 — 이동로봇 내비게이션 지원 (N0~N4)

> 등록: 2026-07-10 (딥리서치 "MoveIt 외 프레임워크/Humble EOL" 파생, 사용자 지시).
> 상위 항목: [phaseE-extras.md](phaseE-extras.md) E.17.
> **비게이트** — 배포판 전환(E.5-4)과 독립: Nav2는 Humble에 정식 존재하므로 지금 추가 가능.

## 왜 하는가

- rosmac의 시뮬 프리셋 2종(panda-moveit, gazebo-diffbot)은 전부 **매니퓰레이션·
  원시 주행** 계열 — ROS 2 4대 프레임워크(Nav2/MoveIt/ros2_control/micro-ROS,
  공식 Related Projects) 중 **이동로봇 내비게이션(Nav2)이 통째로 비어 있다**.
  MoveIt은 팔 전용 플랫폼이고 내비게이션 대체물이 아님(메인테이너 명시,
  딥리서치 3-0 검증) — 바퀴 로봇 사용자는 현재 rosmac에서 갈 곳이 없다.
- 기술적으로는 **기존 프리셋 패턴의 복제**다: 선언적 YAML(vm_apt 주문형 설치 +
  launch + health_topics + foxglove_layout)이라 신규 커맨드·프로비저닝 변경 없이
  `rosmac sim nav2-diffbot` 하나가 추가되는 형태. D 결정 불필요.
- E.15(실로봇 beta)와 시너지: Nav2를 VM에서 돌리고 실로봇(cmd_vel/odom)에 물리는
  구성이 딱 D15 토폴로지의 사용례다.

## 확정 표면 (N0에서 확정할 것)

- 신규 커맨드 없음 — `rosmac sim nav2-diffbot` (+ 기존 sim status/stop/--attach).
- goal 인터페이스: 맥에서 `ros2 action send_goal /navigate_to_pose …`
  (브리지 경유 액션은 MoveGroup 3/3 실측으로 검증된 경로).
- 시각화: Foxglove 레이아웃 1개 (map + robot pose + path; costmap은 Foxglove
  지원 수준을 N0에서 확인).

## 미리 아는 리스크 / 제약

| # | 리스크 | 대응 |
|---|---|---|
| 1 | Humble의 nav2_bringup TB3 데모는 **Gazebo Classic** 의존 — 기존 Fortress(ros-gz)와 조합 마찰, KI-13류 apt 충돌 가능 | N0에서 조합 3안 비교 후 결정(아래). Classic 공존은 최후 수단 |
| 2 | 기존 diffbot.sdf에 **lidar 없음** — SLAM/AMCL/costmap의 입력 부재 | 1안: sdf에 gpu_lidar 추가(Fortress 지원 실측). 안 되면 2안(정적 맵+AMCL 없이 odom 항법)이 아니라 TB3 계열로 폴백 |
| 3 | VM 메모리 8GiB에 Gazebo+SLAM+Nav2 동시 | N1에서 RSS 실측. 초과 시 slam_toolbox 대신 정적 맵 + AMCL로 경량화 |
| 4 | `/map`은 transient_local(latched) — 브리지 통과 여부 | P0.3에서 transient_local 지원 실측됨. N2에서 /map 수신 재확인(안 되면 Foxglove는 VM 8765 직결이라 시각화는 무영향 — 맥 CLI 수신만 제한으로 기록) |
| 5 | Nav2의 /tf 대량 발행 — 2026-07-07 이중발행 사고 패턴 재발 위험 | `rosmac ps` CORE_TOPICS 감시가 이미 있음. N2에서 sim 가동 중 ps 경고 회귀 확인 |
| 6 | lifecycle 노드가 headless에서 자동 activate 안 될 수 있음 | nav2_bringup의 autostart:=true 사용. 실패 시 lifecycle CLI로 수동 활성 절차를 프리셋 launch에 내장 |

## 단계별 계획

### N0 — 설계 확정: 시뮬 조합 선택 (~30분, 조사만)

- **작업**: 세 조합의 근거 조사(설치 크기·의존 충돌·lidar 확보)만으로 결정,
  코드 없음:
  - (a) **기존 diffbot 확장**: diffbot.sdf에 lidar 추가 + slam_toolbox + nav2
    (Fortress 유지, 프리셋 자산 재사용 — 1순위)
  - (b) **정적 맵 경량안**: lidar + 사전 제작 맵 + AMCL + nav2 (SLAM 생략, 메모리 절약)
  - (c) **TB3 폴백**: nav2_bringup tb3 데모 (Gazebo Classic 공존 — 리스크 1 감수)
  - Foxglove의 OccupancyGrid/costmap 패널 지원 확인 → 레이아웃 스코프 확정.
- **AC**: [x] 조합 결정 + 근거를 이 문서에 기록 (아래 N0 결과) [x] apt 패키지
  목록 확정 (버전 핀 포함 — 아래)
- **실패 시 대응**: 셋 다 결격이면 사용자 보고 후 E.17 보류 (규칙: 2회 실패 시 보고).

#### N0 결과 — ✅ 완료 (2026-07-10, 실측)

- **결정: 조합 (a) — 기존 diffbot 확장 (Fortress 유지 + gpu_lidar + slam_toolbox + nav2)**
- 근거 (전부 VM 실측, Ubuntu 22.04 arm64):
  1. **리스크 1 소멸**: `apt-cache depends ros-humble-nav2-bringup` = launch-ros,
     nav2-common, navigation2, **slam-toolbox**, ros-workspace 뿐 — **Gazebo
     Classic/TB3 apt 의존 없음** (TB3 데모 launch가 런타임에 TB3 패키지를 찾을
     뿐이고, 우리는 자체 launch 사용). 조합 (c) 폴백 불필요.
  2. **리스크 2 전망 양호**: `libignition-sensors6-gpu-lidar 6.8.1-1~jammy`
     **이미 설치됨** (OSRF 저장소, KI-13 처방의 부산물). P2.4에서 카메라가 동일
     렌더링 경로(sensors 시스템 + ogre2 + 소프트웨어 EGL)로 통과 → gpu_lidar도
     동일 경로. ros_gz_bridge에 LaserScan gz↔ros 변환 심볼 실측 확인
     (`strings libros_gz_bridge.so`).
  3. Foxglove 3D 패널이 OccupancyGrid(+updates)·Path·LaserScan 전부 지원
     (공식 문서 확인 2026-07-10) → 레이아웃 = 3D 단일 패널(map+scan+path+pose)로 충분.
- **apt 패키지 확정** (dry-run: 신규 99개):
  - `ros-humble-navigation2` **1.1.20**-1jammy.20260613 (메타)
  - `ros-humble-nav2-bringup` **1.1.20**-1jammy.20260613 (slam-toolbox 포함 유발)
  - (`ros-humble-slam-toolbox` **2.6.10**은 bringup 의존으로 자동)
- 추가 확인 필요 사항(N1로 이월): DiffDrive 플러그인 tf(odom→base_link) 브리지
  (`/model/vehicle_blue/tf` gz.msgs.Pose_V → tf2_msgs/TFMessage), base_link→lidar
  정적 tf, lifecycle autostart.

### N1 — VM 스파이크: 자가 완결 내비게이션 (~2시간)

- **작업**: 선택 조합을 VM에서 **수동** 기동(실험 파일 `~/rosmac_spike/nav2/`) —
  headless Gazebo + (SLAM|AMCL) + nav2 lifecycle 자동 활성. VM 안에서
  `/navigate_to_pose` goal 전송 → SUCCEEDED까지.
- **AC**: [x] VM 내 goal → SUCCEEDED 실측 [x] /map·/plan·/tf 발행 확인
  [x] 스택 전체 RSS 실측 (8GiB 대비 여유 기록) [x] 기동~ready 소요 시간
  (health gate timeout 산정 근거)
- **실패 시 대응**: 리스크 1·2 참조. lifecycle hang이면 리스크 6 절차.

#### N1 결과 — ✅ 완료 (2026-07-10, 실측 — 스파이크 파일 `~/rosmac_spike/nav2/`)

- **goal → SUCCEEDED 2/2**: `(0.5, 0.5)`, `(1.0, 1.5)` 연속 성공
  (`ros2 action send_goal /navigate_to_pose`, VM 내 자가완결).
- **구성 확정 사항** (전부 N3 프리셋에 그대로 반영할 것):
  - **`<ignition_frame_id>lidar_link</ignition_frame_id>`가 Fortress에서 동작**
    — /scan frame_id가 스코프명이 아닌 `lidar_link`로 나옴 → 정적 tf
    (`base_link→lidar_link`, x 0.648573 z 0.675)와 정확히 매칭.
  - DiffDrive 플러그인 `<frame_id>odom</frame_id>` +
    `<child_frame_id>base_link</child_frame_id>` + odom 50Hz 동작 —
    tf는 `/model/vehicle_blue/tf`(gz.msgs.Pose_V)를 tf2_msgs로 브리지.
  - `/clock` 브리지(`rosgraph_msgs/Clock[gz.msgs.Clock`) + 전 노드
    use_sim_time:=true 조합 정상.
  - **Nav2 기본 파라미터(navigation_launch.py 무인자)로 충분** — base_link/odom/
    /scan 기본값과 우리 프레임 설계가 일치, 커스텀 nav2_params 불필요.
  - lifecycle: autostart 기본값으로 bt_navigator `active` 자동 도달 (리스크 6 미발생).
- **⚠️ N3 health gate 설계 제약 (핵심 발견)**: slam_toolbox는
  `minimum_travel_distance`(0.2m) **이동 전까지 /map을 0×0으로 latch** —
  health 토픽으로 `/map`을 쓰면 안 됨. `/scan`(ready 즉시 10Hz)을 쓸 것.
- **측정값**: 스택 RSS 합계 **~604MB**, 시스템 사용 848/7931MB (주행 중) —
  8GiB 대비 여유 막대, slam_toolbox 유지 확정 (리스크 3 해소, 조합 (b) 강등 불필요).
  기동→ready(bt_navigator active + /scan 수신) **17s** (스크립트 고정 sleep 13s 포함)
  → health timeout 근거.
- 사소한 함정: DiffDrive는 마지막 cmd_vel 유지(워치독 없음) — 수동 조작 후엔
  zero Twist를 쏴야 정지. Nav2 경유 시엔 무관(종료 시 zero 발행).

### N2 — 브리지 경계 실측 (~1시간)

- **작업**: 맥에서 goal 전송 → SUCCEEDED, `/map`(transient_local)·`/plan`·
  `/amcl_pose` 수신, Foxglove로 지도+로봇+경로 시각화, sim 가동 중
  `rosmac ps` 경고 회귀(이중발행·데몬) 확인, /tf 등 대역 관찰.
- **AC**: [x] 맥 발신 goal 3연속 SUCCEEDED (MoveGroup AC와 동형)
  [x] /map 맥 수신 여부 기록 (리스크 4 — 부정 결과도 기록 가치)
  [~] Foxglove 레이아웃 초안으로 지도·경로 육안 확인 (foxglove_bridge는 VM:8765
  직결이라 스코핑 무관 — 사용자 육안 확인 항목으로 이월) [x] ps 신규 경고 없음
- **실패 시 대응**: 액션 자체가 안 되면 KI-16 지문 확인(RMW). /map만 안 오면
  능력 매트릭스에 조건부 기재하고 진행.

#### N2 결과 — ⚠️ 조건부 PASS (2026-07-11 실측) — **브리지 스코핑 필수 발견 (KI-30)**

- **결론: 기본(unscoped) 브리지로는 맥→nav2 goal이 불가능. 브리지 allow
  스코핑을 적용해야만 동작.** 스코핑 후 맥 발신 goal **3/3 SUCCEEDED**
  `(2,2)→(-2,-1)→(0,0)`, /map(267×343)·/scan·/odom·/plan·/tf·/cmd_vel·/goal_pose
  맥 수신 확인, ps 신규 경고 없음, 스택 RSS 여유(사용 887/7931MB).

- **근본 원인 (KI-30)**: nav2 풀스택은 서비스 **174개** + 액션 12개를 만든다.
  기본 브리지는 이 전부를 zenoh로 내보내 맥 쪽 DDS 디스커버리를 포화시킴 →
  **토픽은 라우팅되나(맥에서 /scan·/odom·/map 수신 OK) 서비스·액션이 라우팅
  실패**. 액션의 하위 토픽(feedback/status)은 맥에 오지만 하위 서비스
  (send_goal/cancel/get_result)는 프록시가 안 생겨 `wait_for_server`가 90초에도
  실패. 일반 서비스 호출(`/bt_navigator/get_parameters`)도 동일하게 멈춤.
  - **판별 실측**: nav2 전부 내리고 VM에 `add_two_ints_server` **단독** 기동 →
    맥 서비스 호출 `sum=42` **즉시 성공**. 즉 브리지·cyclonedds·RMW는 정상,
    순수 **엔티티 수 포화** 문제. (P0.3 단일 talker·P2.3 moveit ~40서비스는
    통과했고 nav2 174서비스는 실패 → 임계는 ~40~174 사이.)

- **해법 (실측 검증)**: VM 브리지를 `-c bridge_scoped.json5`로 기동, `plugins.
  ros2dds.allow`에 nav goal에 필요한 인터페이스만 화이트리스트:
  - `action_servers: ["/navigate_to_pose"]`
  - `publishers: [/scan /odom /map /map_metadata /tf /tf_static /plan
    /global_costmap/costmap /local_costmap/costmap /amcl_pose /clock /rosout]`
  - `subscribers: [/cmd_vel /goal_pose /initialpose]`
  - `service_servers: []`, `service_clients: []` (nav2 내부 서비스는 VM 로컬
    DDS라 스코핑과 무관 — 항법 기능 정상)
  - 브리지 로그: `Route Action Server (ROS:/navigate_to_pose <-> Zenoh:...)
    created` → 맥 `wait_for_server` 40초 내 **SERVER_AVAILABLE**.
  - 스파이크 config: `~/rosmac_spike/nav2/bridge_scoped.json5`

- **⚠️ 아키텍처 함의 (사용자 결정 필요 — D3 인접)**: 현 rosmac 브리지는
  **무스코프**(systemd `zenoh-bridge-ros2dds -l tcp/0.0.0.0:7447`)라 모든
  프리셋을 무제한 브리지한다. nav2(및 대형 스택)를 지원하려면 **브리지에
  스코핑을 도입**해야 하고, 이는 프리셋 추가(YAML 1장) 범위를 넘어 브리지
  아키텍처(D3) 변경이다. N3 착수 전 방식 결정 필요 — [아래 N3 선행 결정] 참조.

### N3 — 프리셋 제품화 (~1.5시간) — **선행 결정 필요 (브리지 스코핑 방식)**

- **⚠️ 선행 결정 (사용자 승인 대기)**: N2가 드러낸 대로 nav2 프리셋은 브리지
  스코핑이 전제다. 방식 후보:
  - **(A) 프리셋별 브리지 스코프** — 프리셋 YAML에 `bridge_allow` 선언, `rosmac
    sim`이 해당 스코프로 VM 브리지를 재기동/복원. 가장 깨끗하나 브리지 생명주기
    (systemd)와 `up/down` 멱등성에 개입. (1순위 제안)
  - **(B) 전역 완화 스코프** — 파라미터·내부 서비스류를 기본 deny하는 상시
    스코프를 모든 프리셋에 적용. 단순하나 기존 검증된 프리셋(panda/diffbot)에
    회귀 위험, 재검증 필요.
  - **(C) VM-shell goal 한정** — 맥 네이티브 goal 포기, `rosmac shell`에서 goal
    전송만 문서화. 가장 약함 — nav2의 맥 네이티브 UX 이점 상실.
- **작업 (결정 후)**: `assets/presets/nav2-diffbot.yaml`(+ `bridge_allow` 필드,
  A안 시) + `nav2-diffbot/` (nav2_world.sdf·nav2-diffbot.launch.py·slam_params.yaml)
  + `layouts/nav2.json`. health_topics=`/scan`(N1: /map은 0.2m 이동 전 0×0 latch라
  부적합), timeout=N1 ready(17s)×1.5≈30s. 자산 초안: `~/rosmac_spike/nav2/`,
  launch 초안: 세션 scratchpad `nav2-diffbot.launch.py.draft`.
- **AC**: [x] A안 구현 [x] `rosmac sim nav2-diffbot` 무인 기동 + health PASS
  [x] 맥에서 goal → SUCCEEDED E2E (3/3) [x] `rosmac sim stop` 잔재 없음
  [x] tests green(97), ruff/mypy clean(CI 방식)
- **실패 시 대응**: health 토픽이 불안정하면 timeout 상향이 아니라 토픽 교체
  (안정 발행 토픽을 N1 실측에서 고를 것).

#### N3 결과 — ✅ 완료 (A안 구현, 2026-07-11 실측)

- **결정: A안(프리셋별 브리지 스코프) 구현 완료** (사용자 승인 2026-07-11).
- **구현** (`src/rosmac/sim.py`):
  - `Preset.bridge_allow: dict | None` 필드 — 6개 allow 카테고리
    (publishers/subscribers/service_servers/service_clients/action_servers/
    action_clients). None이면 무스코프(기존 소형 프리셋 동작 유지).
  - `bridge_scope_config()` — bridge_allow → zenoh allow config(JSON). 미지정
    카테고리는 빈 목록(deny) 명시로 "전부 허용" 누출 차단. doctor C8 왕복 토픽
    `/rosmac/doctor/.*`은 pub/sub에 상시 주입(스코프 중 자가진단 가능).
  - `_apply_bridge_scope()` — config·systemd 드롭인을 **파일로 push**(셸 이스케이프
    회피) 후 sudo로 배치, `daemon-reload`+`restart zenoh-bridge`, 맥 브리지 리셋.
    `start()`에서 launch 전에 호출.
  - `_clear_bridge_scope()` — 드롭인 있으면 제거+무스코프 복원. `stop()`에서
    멱등 호출.
  - 유닛 4종 추가(bridge_allow 파싱·6카테고리·doctor 주입·무스코프 유지), 97 tests.
- **E2E 실측**: `rosmac sim nav2-diffbot --no-viz` → 브리지 자동 스코핑
  (`-c /etc/rosmac/bridge-scope.json5`, `Route Action Server /navigate_to_pose
  created`) → health `/scan` PASS → 서베이 지도(260×268) → **맥 goal 3/3
  SUCCEEDED** `(2,2)→(-2,-1)→(0,0)`. `rosmac sim stop` → 스택 0·드롭인 제거·
  브리지 무스코프 복원·맥 브리지 1개. doctor C8 격리 PASS.
- **구현 중 잡은 함정 2건**:
  - 드롭인을 `printf '%s'`로 쓰면 `\n`이 리터럴로 박혀 systemd 파싱 실패 →
    브리지 무스코프로 조용히 기동. **파일 push 방식으로 수정**(확정).
  - 반복 재기동 시 맥 브리지 고아 누적 → C8 왕복 레이스. `bridge.stop()`이
    `_orphan_pids()`로 고아를 잡으므로 정상 `_reset_mac_bridge`(stop→start)는
    단일 브리지 유지. 누적은 수동 디버깅 잔재였음(실측 확인).
- **알려진 한계(minor)**: 스코프 sim 실행 **중** full `rosmac doctor`의 C8이
  신규 랜덤 토픽 라우트 생성 지연으로 일시 FAIL할 수 있음(격리 실행·수동 왕복은
  PASS). 확정 진단은 sim stop 후 실행 권장. N4에서 문서화.

### N4 — 문서/매트릭스 마감 (~30분)

- **작업**: `assets/presets/nav2-diffbot.yaml` + `nav2-diffbot/` launch 파일 +
  `layouts/nav2.json` 작성. health_topics는 N1 실측 기반(/map 또는 /plan,
  timeout은 N1 ready 시간×1.5). `rosmac sim nav2-diffbot` → health gate PASS →
  맥 goal E2E. 프리셋 파싱 유닛은 기존 test_sim.py 패턴 추가.
- **AC**: [ ] `rosmac sim nav2-diffbot` 무인 기동 + health PASS
  [ ] 맥에서 goal → SUCCEEDED E2E [ ] `rosmac sim stop` 잔재 없음
  (ps로 확인 — 2026-07-07 교훈) [ ] tests green, ruff/mypy clean
- **실패 시 대응**: health 토픽이 불안정하면 timeout 상향이 아니라 토픽 교체
  (안정 발행 토픽을 N1 실측에서 고를 것).

### N4 — 문서/매트릭스 마감 (~30분) — ✅ 완료 (2026-07-11)

- **작업**: README(en/ko) 프리셋 절 nav2-diffbot 행 + 능력 매트릭스 Actions 행에
  Nav2 병기 + 구조적 한계에 브리지 스코핑(KI-30) 항목, workflow(en/ko) Nav2 사용
  절, CHANGELOG(nav2 프리셋 + 함정 28→30), viz `--layout nav2` help/에러 문구.
- **AC**: [x] 영/한 정합 [x] 능력 매트릭스 갱신 (Actions 행에 Nav2 3/3, 스코핑 주석)
- **결과**: README.md·README.ko.md, docs/workflow.md·workflow.ko.md, CHANGELOG.md,
  cli.py(viz help) 갱신. 함정 카운트 README 양쪽 29→30.

## 비목표 (백로그)

- 실로봇 Nav2 배포(로봇 위 Nav2) — E.15 R5(실기) 이후에나 의미
- 멀티맵/웨이포인트 파이프라인, Nav2 플러그인 커스터마이징 가이드
- 배포판 전환(Jazzy/Lyrical)과의 결합 — E.5-4에서 별도 추진
- **맥 env nav2_msgs 자동 설치 (UX 갭)**: `rosmac sim nav2-diffbot`은 VM에 nav2를
  설치하지만, 맥에서 goal을 보내려면 `ros-humble-nav2-msgs`가 맥 env에도 필요.
  현재는 문서 안내뿐 — health(/scan)는 통과하는데 goal이 "server not available"로
  실패하면 사용자가 브리지 문제로 오인하기 쉬움. 프리셋에 맥측 msg 의존 필드
  (`mac_env_pkgs` 등)를 두고 `sim`이 자동 설치하는 개선 후보. (중×소)

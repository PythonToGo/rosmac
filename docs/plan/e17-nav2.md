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
- **AC**: [ ] 조합 결정 + 근거를 이 문서에 기록 [ ] apt 패키지 목록 확정
  (ros-humble-navigation2, nav2-bringup, slam-toolbox 등)
- **실패 시 대응**: 셋 다 결격이면 사용자 보고 후 E.17 보류 (규칙: 2회 실패 시 보고).

### N1 — VM 스파이크: 자가 완결 내비게이션 (~2시간)

- **작업**: 선택 조합을 VM에서 **수동** 기동(실험 파일 `~/rosmac_spike/nav2/`) —
  headless Gazebo + (SLAM|AMCL) + nav2 lifecycle 자동 활성. VM 안에서
  `/navigate_to_pose` goal 전송 → SUCCEEDED까지.
- **AC**: [ ] VM 내 goal → SUCCEEDED 실측 [ ] /map·/plan·/tf 발행 확인
  [ ] 스택 전체 RSS 실측 (8GiB 대비 여유 기록) [ ] 기동~ready 소요 시간
  (health gate timeout 산정 근거)
- **실패 시 대응**: 리스크 1·2 참조. lifecycle hang이면 리스크 6 절차.

### N2 — 브리지 경계 실측 (~1시간)

- **작업**: 맥에서 goal 전송 → SUCCEEDED, `/map`(transient_local)·`/plan`·
  `/amcl_pose` 수신, Foxglove로 지도+로봇+경로 시각화, sim 가동 중
  `rosmac ps` 경고 회귀(이중발행·데몬) 확인, /tf 등 대역 관찰.
- **AC**: [ ] 맥 발신 goal 3연속 SUCCEEDED (MoveGroup AC와 동형)
  [ ] /map 맥 수신 여부 기록 (리스크 4 — 부정 결과도 기록 가치)
  [ ] Foxglove 레이아웃 초안으로 지도·경로 육안 확인 [ ] ps 신규 경고 없음
- **실패 시 대응**: 액션 자체가 안 되면 KI-16 지문 확인(RMW). /map만 안 오면
  능력 매트릭스에 조건부 기재하고 진행.

### N3 — 프리셋 제품화 (~1.5시간)

- **작업**: `assets/presets/nav2-diffbot.yaml` + `nav2-diffbot/` launch 파일 +
  `layouts/nav2.json` 작성. health_topics는 N1 실측 기반(/map 또는 /plan,
  timeout은 N1 ready 시간×1.5). `rosmac sim nav2-diffbot` → health gate PASS →
  맥 goal E2E. 프리셋 파싱 유닛은 기존 test_sim.py 패턴 추가.
- **AC**: [ ] `rosmac sim nav2-diffbot` 무인 기동 + health PASS
  [ ] 맥에서 goal → SUCCEEDED E2E [ ] `rosmac sim stop` 잔재 없음
  (ps로 확인 — 2026-07-07 교훈) [ ] tests green, ruff/mypy clean
- **실패 시 대응**: health 토픽이 불안정하면 timeout 상향이 아니라 토픽 교체
  (안정 발행 토픽을 N1 실측에서 고를 것).

### N4 — 문서/매트릭스 마감 (~30분)

- **작업**: README(en/ko) 프리셋 절에 nav2-diffbot 행 + 능력 매트릭스 Actions
  행 증거에 Nav2 추가(MoveGroup과 병기), workflow.md(en/ko) 시뮬 절 한 줄,
  CHANGELOG. viz `--layout nav2` 등록.
- **AC**: [ ] 영/한 정합 [ ] E.14 매트릭스 갱신(실측 링크)

## 비목표 (백로그)

- 실로봇 Nav2 배포(로봇 위 Nav2) — E.15 R5(실기) 이후에나 의미
- 멀티맵/웨이포인트 파이프라인, Nav2 플러그인 커스터마이징 가이드
- 배포판 전환(Jazzy/Lyrical)과의 결합 — E.5-4에서 별도 추진

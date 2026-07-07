# Phase 2 — 시뮬레이션·시각화 통합 (MoveIt / Gazebo / Foxglove)

> 목표: `rosmac sim <preset>` 한 줄로 VM에서 시뮬레이션 스택이 뜨고,
> 맥의 Foxglove에서 즉시 보이며, 맥 네이티브 노드로 제어할 수 있게 한다.
> 착수 조건: Phase 1 E2E 통과
> E2E 성공 기준: 맥의 rclpy 노드가 MoveIt 액션 goal 전송 → VM에서 플래닝/실행 →
> 맥 Foxglove 3D 패널에서 로봇 팔이 움직이는 것을 실시간 확인.
> 예상 소요: 2~3주 (파트타임)

## 태스크 의존 그래프

```
2.1 foxglove_bridge 자동화 ─┐
2.2 프리셋 시스템           ─┼→ 2.3 프리셋: panda-moveit → 2.6 맥 네이티브 제어 예제 → 2.7 E2E
                            └→ 2.4 프리셋: gazebo-diffbot
2.5 Foxglove 레이아웃은 2.3/2.4에 종속
```

---

## 2.1 foxglove_bridge 자동화

### 배경
Foxglove는 DDS를 직접 말하지 않고 websocket(`foxglove_bridge`, 기본 8765)로 붙는다.
**설계 결정**: foxglove_bridge는 **VM 쪽**에서 돌린다.
- 이유: 시뮬레이션 데이터(고대역 센서)가 zenoh 브리지를 거치지 않고
  VM→8765 포트포워딩→Foxglove로 직행 → R4(브리지 병목) 우회.
- 맥 네이티브 노드의 토픽도 zenoh 브리지를 타고 VM DDS에 보이므로 함께 시각화됨.

### 수행 절차
1. 프로비저닝에 추가: `apt install ros-humble-foxglove-bridge`
   (`assets/provision/30-foxglove.sh`, systemd 유닛 — zenoh와 동일 패턴,
   단 기본 disabled: `rosmac up --viz` 또는 sim 실행 시에만 start)
2. `rosmac up`에 `--viz` 플래그: VM 쪽 `systemctl start foxglove-bridge` + 맥에서
   Foxglove 앱 설치 여부 확인(`/Applications/Foxglove*.app` glob), 없으면 안내 출력.
3. `rosmac viz` 서브커맨드: bridge 기동 확인 후
   `open "foxglove://open?ds=foxglove-websocket&ds.url=ws://localhost:8765"`
   (딥링크가 안 되면 앱 열고 URL 안내 출력 — 실측 후 결정, 결과 기록)

### 완료 기준 (AC)
- [ ] `rosmac viz` 실행 → Foxglove가 연결되고 VM의 `/chatter` 토픽이 Raw Messages 패널에 보임
- [ ] transient_local `/robot_description`이 Foxglove 3D 패널에서 URDF로 로드됨
      (Phase 0.3 QoS 케이스의 실전 검증 — 실패 시 foxglove_bridge는 VM 로컬 DDS를
      직접 보므로 브리지 QoS와 무관하게 동작해야 정상. 안 되면 별도 이슈로 조사)

---

## 2.2 프리셋 시스템 (`rosmac sim`)

### 설계
프리셋 = 선언적 YAML (`src/rosmac/assets/presets/<name>.yaml`):
```yaml
name: panda-moveit
description: "Panda 팔 + MoveIt move_group (RViz 없음, Foxglove 시각화)"
vm_apt:                          # 최초 실행 시 VM에 설치 (멱등: dpkg -s 로 확인)
  - ros-humble-moveit
  - ros-humble-moveit-resources
vm_env:
  ROS_LOCALHOST_ONLY: "1"
launch:                          # VM에서 실행할 명령 (foreground, rosmac이 수명 관리)
  cmd: "ros2 launch <검증 후 확정> use_rviz:=false"
foxglove_layout: panda.json      # assets/layouts/
health_topics:                   # 기동 성공 판정용 — 이 토픽들이 N초 내에 보여야 함
  - { name: /joint_states, timeout: 20 }
  - { name: /monitored_planning_scene, timeout: 30 }
```

### `rosmac sim <name>` 동작 명세
1. `doctor --json`으로 사전 점검 (C2, C5~C8 FAIL이면 중단 + 안내)
2. `vm_apt` 미설치분 설치 (진행 표시)
3. VM에서 `launch.cmd`를 **tmux 세션**(`rosmac-sim`)으로 실행
   - tmux인 이유: `rosmac sim --attach`로 로그 관찰, 세션 유지, 이중 실행 감지가 쉬움
4. `health_topics` 폴링 — 전부 등장하면 "READY" + Foxglove 자동 오픈(2.1 재사용)
5. `rosmac sim stop` / `rosmac sim status` / `rosmac sim --attach`

### 완료 기준 (AC)
- [ ] 존재하지 않는 프리셋 이름 → 사용 가능 목록 출력
- [ ] 이중 실행 시도 → 기존 세션 안내 (R6 패턴)
- [ ] health_topics 타임아웃 시 → tmux 로그 마지막 30줄 출력 + 실패 종료

---

## 2.3 프리셋 1: panda-moveit

### 사전 검증 태스크 (계획 시점 불확실성 — 반드시 실측)
MoveIt 데모 launch의 apt 배포 경로가 유동적이다. VM에서 아래 순서로 후보 확인:
1. `ros2 launch moveit_resources_panda_moveit_config demo.launch.py use_rviz:=false`
   (`ros-humble-moveit-resources` 계열이 제공하는지 `ros2 pkg files`로 확인)
2. 안 되면 `ros-humble-moveit-configs-utils` + 최소 커스텀 launch 파일을
   프리셋 자산으로 동봉 (`assets/presets/panda-moveit/demo.launch.py`)
   — move_group + robot_state_publisher + ros2_control fake hardware 구성
3. 확정된 경로를 프리셋 YAML에 반영하고 `phase2-results.md`에 기록

### 검증 절차
```bash
rosmac sim panda-moveit
# 맥에서:
ros2 topic echo /joint_states --once            # 관절 상태 수신
ros2 action list | grep move_action             # MoveIt 액션 노출 확인
ros2 action send_goal /move_action moveit_msgs/action/MoveGroup "<간단 goal yaml>"
```
goal yaml은 named target(`ready` 등) 기반 최소 구성으로 프리셋에 예제 동봉.

### 완료 기준 (AC)
- [ ] `rosmac sim panda-moveit` → READY까지 무인 도달
- [ ] 맥에서 `/move_action` goal 전송 → SUCCEEDED result 수신 (**브리지 경유 액션의 실전 검증**)
- [ ] Foxglove 3D 패널에서 팔 자세 변화 확인

---

## 2.4 프리셋 2: gazebo-diffbot (Gazebo Fortress headless)

### 배경 결정
- Humble 페어링은 **Gazebo Fortress** (`ros-humble-ros-gz`, 실행 명령 `ign gazebo`).
- **headless 원칙**: `ign gazebo -s -r <world>` (서버만). GUI는 띄우지 않는다 —
  시각화는 센서/상태 토픽을 Foxglove로 본다. (리서치에서 확인된 VM GUI 스트리밍
  병목을 설계로 회피)

### 수행 절차
1. `vm_apt`: `ros-humble-ros-gz`, (월드/모델용) `ros-humble-ros-gz-sim-demos` 존재 확인
2. 데모 월드 선정: diff drive 데모 (`ros_gz_sim_demos` 제공분 실측 후 확정)
3. `ros_gz_bridge` 설정: `/cmd_vel`(맥→VM), `/odom`, `/tf`, 카메라 `/image`(VM→Foxglove)
   — bridge yaml을 프리셋 자산으로 동봉
4. 성능 측정 및 기록 (R3 데이터):
   - `ign gazebo -s` RTF(real time factor) — 물리만일 때
   - 카메라 센서 활성 시 RTF와 `/image` fps (`ros2 topic hz`)
   - 결과가 RTF < 0.5면 프리셋 기본값을 센서 저해상도로 조정 + Phase 3 동기 강화

### 검증 절차
```bash
rosmac sim gazebo-diffbot
# 맥에서:
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}}"
# Foxglove: odom 경로가 3D 패널에서 이동, 카메라 이미지 패널 표시
```

### 완료 기준 (AC)
- [ ] READY 무인 도달, 맥에서 `/cmd_vel`로 로봇 이동
- [ ] Foxglove에서 odom + 카메라 이미지 확인
- [ ] RTF/fps 수치 기록 (`phase2-results.md`)

---

## 2.5 Foxglove 레이아웃 템플릿

### 수행 절차
1. 2.3/2.4를 손으로 시각화하며 만든 레이아웃을 Foxglove에서 export →
   `assets/layouts/panda.json`, `diffbot.json`
2. panda: 3D(URDF+TF+PlanningScene) / Raw(/joint_states) / Log 패널
   diffbot: 3D(odom 경로) / Image / Plot(선속도) 패널
3. `rosmac viz --layout <preset>`: Foxglove 딥링크/CLI의 레이아웃 지정 지원 여부 실측.
   미지원이면 "File > Import Layout" 안내 출력으로 대체 (결정 기록).

### 완료 기준 (AC)
- [ ] 새 Foxglove 설치 상태에서 레이아웃 import → 패널 구성 재현

---

## 2.6 맥 네이티브 개발 워크플로 예제

### 목적
"맥에서 코드 작성 → VM 스택 제어"라는 프로젝트의 존재 이유를 예제로 증명 + 문서화.

### 수행 절차
1. 예제 패키지 `examples/pick_demo/` (rclpy):
   - `MoveGroup` 액션 클라이언트로 named target 순회 (ready → extended → ready)
   - 맥에서 `colcon build` (RoboStack env) 후 실행
2. 문서 `docs/workflow.md`:
   - `rosmac shell`에서의 개발 루프 (colcon, 디버거 붙이기)
   - 토픽이 어느 경로로 흐르는지 다이어그램 (zenoh vs foxglove 8765)
   - 흔한 함정: env var 빠짐, 이중 브리지, QoS 불일치 — doctor 항목과 상호 링크

### 완료 기준 (AC)
- [ ] 맥에서 빌드한 pick_demo가 VM MoveIt을 구동 (2.7의 본체)

---

## 2.7 Phase 2 E2E 수용 테스트

### 시나리오
```
1. rosmac up --viz
2. rosmac sim panda-moveit           → READY
3. (맥, rosmac shell) ros2 run pick_demo pick_demo
4. 관찰: Foxglove 3D에서 팔이 3개 자세를 순회
5. pick_demo가 3회 모두 SUCCEEDED 로그 출력 후 exit 0
6. rosmac sim stop && rosmac down    → 잔여 프로세스 0
```

### 완료 기준 (AC)
- [ ] 시나리오 무인 통과 (Foxglove 육안 확인 항목 제외한 전 단계 스크립트화)
- [ ] `docs/plan/phase2-results.md` 작성: RTF/fps/레이턴시 수치,
      확정된 launch 경로, 발견한 버그와 해결책
- [ ] 이 시점에서 README.md 작성 (설치→sim까지 quickstart) — 사실상 v0.1 릴리스 가능 상태

---

## 부록 A — MoveGroup 액션 클라이언트 스켈레톤 (2.3 검증 + 2.6 예제의 핵심부)

CLI로 MoveGroup goal YAML을 손으로 쓰는 것은 오류 유발적이다(중첩 깊음).
**named target 방식의 rclpy 클라이언트**를 쓴다 — 2.3 검증과 2.6 pick_demo가 공유:

```python
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint

# 요지: named target("ready" 등)은 MoveGroup 액션에 직접 필드가 없으므로,
# 해당 자세의 관절값을 JointConstraint 목록으로 넣는 방식이 가장 이식성 높다.
# panda "ready" 관절값 (moveit_resources panda_moveit_config의 srdf 기준):
READY = {"panda_joint1": 0.0, "panda_joint2": -0.785, "panda_joint3": 0.0,
         "panda_joint4": -2.356, "panda_joint5": 0.0, "panda_joint6": 1.571,
         "panda_joint7": 0.785}
# ⚠️ 실측 시 VM에서 srdf의 group_state를 확인해 값 대조:
#   ros2 run <pkg> ... 또는 srdf 파일 직접 grep: group_state name="ready"

class MoveClient(Node):
    def __init__(self):
        super().__init__("pick_demo")
        self.client = ActionClient(self, MoveGroup, "/move_action")

    def goal_for(self, joints: dict) -> MoveGroup.Goal:
        g = MoveGroup.Goal()
        g.request.group_name = "panda_arm"          # srdf의 그룹명 — 실측 확인
        g.request.allowed_planning_time = 5.0
        c = Constraints()
        c.joint_constraints = [
            JointConstraint(joint_name=k, position=v,
                            tolerance_above=0.01, tolerance_below=0.01, weight=1.0)
            for k, v in joints.items()]
        g.request.goal_constraints = [c]
        g.planning_options.plan_only = False        # 플래닝+실행
        return g
```
판정: result의 `error_code.val == 1` (moveit_msgs SUCCESS). 그 외 코드는
moveit_msgs/msg/MoveItErrorCodes 상수표와 대조해 결과 리포트에 기록.

## 부록 B — 기대 신호 (2.3 / 2.4 READY 판정과 육안 확인의 구체화)

**panda-moveit READY 시점의 VM 로그 (tmux에서):**
```
[move_group-N] ... MoveGroup context initialization complete
You can start planning now!
```
이 두 줄이 health_topics 폴링의 백업 판정 기준이다 (로그 grep도 병용 가능).

**gazebo-diffbot 판정:**
```
# RTF 확인 (VM):
ign stats   # 또는 토픽: ign topic -e -t /stats  → real_time_factor 필드
# 이동 판정 (맥) — /odom의 x가 증가하는지:
ros2 topic echo /odom --field pose.pose.position.x   # 값이 단조 증가하면 PASS
```

**Foxglove 육안 확인 항목의 증거 규칙**: 3D 패널에 로봇이 보이는 화면과
움직인 후 화면 2장을 `docs/plan/evidence/phase2-*.png`로 저장 (AGENTS.md 5절).

## 부록 C — 프리셋 launch 경로가 전부 실패할 때의 최후 폴백 (2.3)

후보 1·2가 모두 안 되면, 프리셋 자산에 **완전 자립형 launch**를 동봉하는 것으로 전환:
`moveit_configs_utils.MoveItConfigsBuilder("moveit_resources_panda")`로
move_group + robot_state_publisher + ros2_control(fake) + spawner를 구성한다.
MoveIt 공식 튜토리얼 리포의 demo launch 구조를 참고하되, **소스 빌드가 필요한
moveit2_tutorials 패키지 자체에 의존하지 말 것** (apt 배포분 + 동봉 launch만으로 성립해야
`rosmac sim`의 "무인 설치" 원칙이 지켜진다). 이 폴백을 쓰게 되면 결정 기록 후
launch 파일을 `assets/presets/panda-moveit/`에 커밋.

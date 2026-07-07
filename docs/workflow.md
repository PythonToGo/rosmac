# rosmac 개발 워크플로 — 맥에서 코드 작성, VM 스택 제어

> 이 문서는 "맥 네이티브 개발 루프"가 실제로 어떻게 도는지를 예제(pick_demo)로 보여준다.
> 환경 구축은 README의 Quickstart를 먼저 끝낼 것 (`rosmac init && rosmac up`).

## 1. 데이터가 흐르는 두 개의 경로

```
┌─ macOS ────────────────────────────────────────────────────┐
│  ① 개발 루프: rosmac shell → colcon build → ros2 run …      │
│     (RoboStack conda env, rclpy 노드가 맥에서 실행됨)        │
│                                                            │
│  [zenoh-bridge (맥)] ←→ tcp:7447 ←→ [zenoh-bridge (VM)]     │
│     ↑ 토픽/서비스/액션이 이 경로로 VM DDS와 투명하게 연결      │
│                                                            │
│  Foxglove 앱 ←── ws:8765 ──── [foxglove_bridge (VM)]        │
│     ↑ 시각화는 zenoh를 거치지 않고 VM DDS 직결 (고대역 우회)   │
│  ┌─ Lima VM (Ubuntu 22.04 arm64) ───────────────────────┐  │
│  │  move_group / Gazebo / ros_gz_bridge / systemd 브리지  │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

- **zenoh 경로** (7447): 맥의 rclpy/rclcpp 노드 ↔ VM 노드 간 토픽·서비스·액션.
- **foxglove 경로** (8765): 시각화 전용. VM 로컬 DDS를 직접 보므로 zenoh 브리지
  상태와 무관하고, 카메라 같은 고대역 토픽도 병목 없이 흐른다 (설계: phase2 2.1).

## 2. 개발 루프 (pick_demo 기준)

```bash
rosmac up                      # VM + 브리지 기동
rosmac sim panda-moveit        # VM에서 MoveIt 스택 기동, READY까지 대기

rosmac shell                   # ROS env가 주입된 서브셸 진입 — env 수동 설정 0회
cd ~/workspace/rosmac/examples
colcon build                   # 맥 네이티브 빌드 (RoboStack)
source install/setup.zsh
ros2 run pick_demo pick_demo   # 맥에서 실행 → VM MoveIt이 플래닝/실행
```

pick_demo는 MoveGroup 액션 클라이언트로 named target(ready→extended→ready)을
순회한다. goal은 zenoh 브리지를 건너 VM의 `/move_action`으로 전달되고,
feedback/result가 되돌아온다. Foxglove 3D 패널에서 팔이 움직이는 것이 보인다.

디버거는 평범한 파이썬처럼 붙는다: `rosmac shell` 안에서
`python -m pdb $(which pick_demo)` 또는 IDE 인터프리터를
`~/micromamba/envs/ros_env/bin/python`으로 지정.

## 3. 흔한 함정 (막히면 `rosmac doctor` 먼저)

| 증상 | 원인 | 도구 |
|---|---|---|
| 토픽이 안 보임 / 가끔 보임 | env var 누락 (ROS_LOCALHOST_ONLY 등) — 맨 셸에서 ros2 실행 | doctor C4, `rosmac shell` 사용 (KI-6) |
| 같은 메시지 2번 수신 | 브리지 비정상 종료 잔재 | `rosmac down --keep-vm && rosmac up` (KI-17) |
| 서비스/액션만 무응답 | RMW가 fastrtps로 샘 | doctor C4 — 반드시 cyclonedds (KI-16, D9) |
| 노드가 "participant index" 에러로 죽음 | CycloneDDS 참가자 10개 제한 | rosmac이 주입하는 CYCLONEDDS_URI 확인 (KI-23) |
| `ros2 run`이 실행 파일을 못 찾음 | setuptools가 bin/에 설치 | 패키지에 setup.cfg 추가 (KI-22) |
| VM 명령에서 ros2 not found | bash -lc는 .bashrc 소싱 안 됨 | `rosmac shell --vm -c` 사용 (KI-19) |

전체 함정 DB: [docs/plan/known-issues.md](plan/known-issues.md)

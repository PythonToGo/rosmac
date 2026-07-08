# rosmac

**Apple Silicon Mac에서 ROS2 Humble + MoveIt + Gazebo 개발을 명령어 몇 개로.**

ROS2는 macOS를 사실상 지원하지 않는다 (Tier 3, Apple Silicon은 목록에도 없음).
rosmac은 이를 레이어 분리로 우회한다: 개발은 맥 네이티브(RoboStack), 무거운 스택은
Lima VM의 Ubuntu 22.04 arm64(Tier 1), 시각화는 맥 Foxglove, 경계는 zenoh 브리지.

```
개발(rclpy/colcon, 맥) ↔ zenoh(tcp:7447) ↔ VM(MoveIt·Gazebo) → Foxglove(ws:8765, 맥)
```

## 지원 매트릭스

| 항목 | 지원 | 비고 |
|---|---|---|
| HW | Apple Silicon (M1 이상) | **Intel Mac 비지원** (검증 수단 없음) |
| OS | macOS 14 (Sonoma) 이상 | 실측: macOS 26.x / M3 Pro / 18GB |
| Python | 3.11+ | 실측: 3.12 |
| ROS 2 | Humble (양측 rmw_cyclonedds_cpp 고정) | VM: Ubuntu 22.04 arm64 |

버전 정책: [SemVer](https://semver.org/lang/ko/). **0.y.z 동안은 마이너 버전이
breaking change를 포함할 수 있다.** 변경 이력은 [CHANGELOG.md](CHANGELOG.md).

## 요구 사항

- [Homebrew](https://brew.sh), 디스크 여유 ≥ 40GB
- [Foxglove 앱](https://foxglove.dev/download) (시각화용, 선택)

## Quickstart (실측 기준 ~6분, 다운로드 캐시 없으면 +10분)

```bash
brew install lima micromamba
git clone https://github.com/PythonToGo/rosmac && cd rosmac
python3.12 -m venv .venv && .venv/bin/pip install -e .
export PATH="$PWD/.venv/bin:$PATH"

rosmac init      # conda env + 브리지 바이너리 + VM 프로비저닝 (전 단계 멱등)
rosmac up        # VM + 양측 zenoh 브리지 기동
rosmac doctor    # C1~C11 진단 — C8이 토픽 왕복까지 자가 검증
```

동작 확인:

```bash
rosmac shell --vm -c 'nohup ros2 run demo_nodes_cpp talker >/dev/null 2>&1 & echo ok'
rosmac shell -c 'ros2 topic echo /chatter --once'   # 맥에서 VM 토픽 수신
```

## 시뮬레이션 프리셋

```bash
rosmac sim panda-moveit     # MoveIt(Panda 팔) — 맥에서 /move_action 사용 가능
rosmac sim gazebo-diffbot   # Gazebo Fortress headless + 전방 카메라
rosmac sim list / status / stop / --attach
rosmac viz --layout panda   # Foxglove 연결 (+레이아웃 안내)
```

맥 네이티브 개발 루프와 예제(pick_demo)는 [docs/workflow.md](docs/workflow.md) 참조.

## 내 프로젝트 가져오기 (Phase 4)

```bash
rosmac deps ~/my_ws --install   # package.xml 의존성 → RoboStack 패키지 설치 (rosdep 대체)
rosmac shell                    # 이 안에서의 colcon build는 구식 CMake 함정(KI-25) 자동 우회
rosmac ps                       # 막히면: 맥+VM 프로세스·토픽 발행자 한 화면 진단
rosmac push ~/my_ws --build     # 맥에서 안 빌드되는 패키지(libfranka 등)는 VM에서
```

## 커맨드 요약

| 커맨드 | 역할 |
|---|---|
| `rosmac init` | 의존성/conda env/브리지/VM 준비 (멱등, 재실행 시 스킵) |
| `rosmac up` / `down` / `status` | 스택 기동/정지/상태 (`--keep-vm`, `--viz`) |
| `rosmac doctor` | 11항 진단 + 처방 (`--json`) |
| `rosmac shell` | ROS env 주입 서브셸 (`--vm`, `-c`) — colcon 기본값 자동 주입 |
| `rosmac deps <ws>` | package.xml 의존성 점검·설치 (`--install`, `--json`) |
| `rosmac ps` | 맥+VM ROS 프로세스·핵심 토픽 발행자 관찰 (`--json`) |
| `rosmac push <ws>` | 워크스페이스를 VM으로 복사 (+`--build`) — linux 전용 패키지용 |
| `rosmac sim <preset>` | VM 시뮬 스택 tmux 기동 + health 판정 |
| `rosmac viz` | foxglove_bridge 기동 + 앱 딥링크 |

## 실측 성능 (M3 Pro, 2026-07)

- 브리지 대역폭: 10.3 MB/s (1MB@10Hz 드랍 없음)
- MoveGroup 액션 왕복: 플래닝+실행 goal 3연속 SUCCEEDED
- Gazebo Fortress headless RTF: 물리만 1.00 / 카메라(320x240@15Hz) 0.99
- 카메라 스트림: VM 14.4fps → 맥 14.4fps (무손실)

## 아키텍처·설계 결정

[PLAN.md](PLAN.md)의 결정 로그와 리스크 레지스터,
막히면 [docs/plan/known-issues.md](docs/plan/known-issues.md) (함정 28개 실측 DB).

## 라이선스

MIT

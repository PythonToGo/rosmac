# rosmac

**맥에서 ROS 2를 명령어 하나로 — 개발은 macOS 네이티브(rclpy/colcon), 무거운 스택은 Tier-1 우분투, 둘 사이는 TCP 포트 하나.**

[English (main)](README.md)

ROS 2는 macOS를 사실상 지원하지 않는다 (Tier 3, Apple Silicon은 목록에도 없음). 기존
우회로는 각자 벽에 부딪힌다: macOS Docker에는 `--network=host`가 없어 호스트↔컨테이너
DDS 디스커버리가 구조적으로 단절되고, 순수 VM은 맥 쪽 툴체인 통합을 포기하며,
RoboStack에 osx-arm64 패키지가 의외로 많이 있지만 무거운 스택(MoveIt, Gazebo)은
*존재해도 신뢰하기 어렵다* — dylib 깨짐과 런타임 크래시가 실측으로 확인된다.

rosmac은 문제와 싸우는 대신 문제를 분할한다:

```
개발은 맥 네이티브 (RoboStack: rclpy, colcon, ros2 CLI)
        ↕  zenoh 브리지 — TCP 포트 하나(7447), 경계에 DDS 멀티캐스트 없음
무거운 스택은 Tier 1에서 (Lima VM, Ubuntu 22.04 arm64: MoveIt, Gazebo)
        →  시각화는 맥에서 (Foxglove, ws:8765)
        ⇢  선택: 같은 LAN의 실로봇 — TCP 엔드포인트 하나 추가, 같은 모델
           (beta, [docs/robot-setup.ko.md](docs/robot-setup.ko.md))
```

설치 스크립트 이상인 이유:

- **`rosmac doctor`** — 알려진 고장 모드 16항 점검, `--fix`로 안전한 항목 자동 수리
  (hung ros2 데몬, 고아 브리지, 깨진 lima 포트 규칙). **실측 함정 30개 DB** 위에서
  만들어졌다.
- **`rosmac deps`** — 워크스페이스 `package.xml` 의존성을 RoboStack conda 패키지로
  매핑 (conda를 아는 rosdep 대체).
- **`rosmac push --build`** — 리눅스 전용 패키지는 VM으로 복사해 거기서 빌드.
- **`rosmac report`** — 이슈 첨부용 진단 번들 tar.gz 하나 (`~/.rosmac` 밖은 수집 안 함).

## 지원 매트릭스

| 항목 | 지원 | 비고 |
|---|---|---|
| HW | Apple Silicon (M1 이상) | **Intel Mac 비지원** (검증 수단 없음) |
| OS | macOS 14 (Sonoma) 이상 | 실측: macOS 26.x / M3 Pro / 18GB |
| Python | 3.11+ | 실측: 3.12 |
| ROS 2 | Humble (양측 rmw_cyclonedds_cpp 고정) | VM: Ubuntu 22.04 arm64 |

버전 정책: [SemVer](https://semver.org/lang/ko/). **0.y.z 동안은 마이너 버전이
breaking change를 포함할 수 있다.** 변경 이력은 [CHANGELOG.ko.md](CHANGELOG.ko.md).

## 요구 사항

- [Homebrew](https://brew.sh), 디스크 여유 ≥ 40GB
- [Foxglove 앱](https://foxglove.dev/download) (시각화용, 선택)

## Quickstart (실측 ~6분, 다운로드 캐시 없으면 +10분)

```bash
brew install lima micromamba
git clone https://github.com/PythonToGo/rosmac && cd rosmac
python3.12 -m venv .venv && .venv/bin/pip install -e .
export PATH="$PWD/.venv/bin:$PATH"

rosmac init      # conda env + 브리지 바이너리 + VM 프로비저닝 (전 단계 멱등)
rosmac up        # VM + 양측 zenoh 브리지 기동
rosmac doctor    # 16항 진단 — C8이 토픽 왕복까지 자가 검증
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
rosmac sim nav2-diffbot     # Nav2 이동로봇 내비게이션 — 맥에서 /navigate_to_pose
rosmac sim list / status / stop / --attach
rosmac viz --layout nav2    # Foxglove 연결 (+레이아웃 안내)
```

`nav2-diffbot`은 벽 아레나에서 라이다 diffbot에 SLAM+Nav2를 돌린다. `/cmd_vel`로
주행해 지도를 만든 뒤 맥에서 `/navigate_to_pose` goal을 보낸다. Nav2 풀스택도
기본 브리지로 동작한다 — `rosmac sim`이 시작 시 브리지 세션을 리셋해 새 스택이
신선한 라우트를 받게 한다(KI-17).

맥 네이티브 개발 루프와 예제(pick_demo)는 [docs/workflow.ko.md](docs/workflow.ko.md) 참조.

## 내 프로젝트 가져오기

```bash
rosmac deps ~/my_ws --install   # package.xml 의존성 → RoboStack 패키지 설치 (rosdep 대체)
rosmac shell                    # 이 안에서의 colcon build는 구식 CMake 함정 자동 우회
rosmac ps                       # 막히면: 맥+VM 프로세스·토픽 발행자 한 화면 진단
rosmac push ~/my_ws --build     # 맥에서 안 빌드되는 패키지(libfranka 등)는 VM에서
```

## 커맨드 요약

| 커맨드 | 역할 |
|---|---|
| `rosmac init` | 의존성/conda env/브리지/VM 준비 (멱등, 재실행 시 스킵) |
| `rosmac up` / `down` / `status` | 스택 기동/정지/상태 (`--keep-vm`, `--viz`) |
| `rosmac doctor` | 16항 진단 + 처방 (`--json`, `--fix` 안전 항목 자동 수리) |
| `rosmac shell` | ROS env 주입 서브셸 (`--vm`, `-c`) — colcon 기본값 자동 주입 |
| `rosmac deps <ws>` | package.xml 의존성 점검·설치 (`--install`, `--json`) |
| `rosmac ps` | 맥+VM ROS 프로세스·핵심 토픽 발행자 관찰 (`--json`) |
| `rosmac push <ws>` | 워크스페이스를 VM으로 복사 (+`--build`) — linux 전용 패키지용 |
| `rosmac sim <preset>` | VM 시뮬 스택 tmux 기동 + health 판정 |
| `rosmac viz` | foxglove_bridge 기동 + 앱 딥링크 |
| `rosmac report` | 이슈 첨부용 진단 번들 생성 (~/.rosmac 밖은 수집 안 함) |
| `rosmac uninstall` | rosmac이 만든 것 전부 제거 (conda env, VM, ~/.rosmac) |

exit code 규약:

| code | 의미 | 예 |
|---|---|---|
| 0 | 성공 | |
| 1 | 실행 실패 (환경·상태 문제) | VM 미기동, conda env 없음, 브리지/빌드 실패 |
| 2 | 사용법·설정 오류 (입력을 고치면 됨) | 잘못된 프리셋·레이아웃 이름, src/ 없는 워크스페이스, config.yaml 오류 |

오류는 원인+처방 패널로 출력되며, 예상 밖 오류만 traceback을 보여준다
(그 경우 `rosmac report` 번들과 함께 이슈로 제보).

## 실측 성능 (M3 Pro, 2026-07)

- 브리지 대역폭: 10.3 MB/s (1MB@10Hz 드랍 없음)
- MoveGroup 액션 왕복: 플래닝+실행 goal 3연속 SUCCEEDED
- 맥에서 Nav2 `/navigate_to_pose`: goal 3연속 SUCCEEDED (기본 브리지)
- Gazebo Fortress headless RTF: 물리만 1.00 / 카메라(320x240@15Hz) 0.99
- 카메라 스트림: VM 14.4fps → 맥 14.4fps (무손실)

## 브리지 능력 매트릭스 (2026-07 실측)

맥 ↔ VM zenoh 브리지 너머에서 동작하는 것:

| ROS 2 기능 | 상태 | 실측 근거 / 비고 |
|---|---|---|
| Topics | ✅ | 양방향 pub/sub; 10.3 MB/s @ 10Hz 무손실. 새 토픽의 첫 구독은 라우트 생성에 몇 초 소요 |
| Services | ✅ | 핀된 CycloneDDS RMW 필수 — Fast DDS는 디스커버리는 되는데 모든 호출이 타임아웃 (KI-16; RMW를 핀한 이유) |
| Actions | ✅ | MoveGroup 플래닝+실행 goal 3/3 SUCCEEDED; 맥에서 Nav2 `/navigate_to_pose` 3/3 SUCCEEDED (풀스택, 기본 브리지) |
| Parameters | ⚠️ 부분 | 원시 파라미터 서비스(`get/set_parameters` 등)는 `ros2 service call`로 동작; `ros2 param` CLI는 **불가** — 브리지가 원격 노드를 노드 그래프에 미러링하지 않아 `ros2 node list`에 VM 노드가 안 보임 |
| rosbag2 | ✅ | 맥에서 VM 토픽 녹화(무손실)·VM 내 녹화·양쪽 어디서 재생해도 반대편 도달. VM bag 회수는 `limactl cp -r rosmac:/path ~/dest` (D16) — [docs/workflow.ko.md](docs/workflow.ko.md) 참조 |
| Robot link (LAN) | 🧪 beta | `robot:` 설정 → 맥 브리지가 로봇 쪽 브리지로 TCP 엔드포인트 추가 (D15). 대리 로봇(제2 VM) 실측: 토픽/서비스 10 MB/s @ 10Hz 무손실, 서비스 RTT < 1 ms, 로봇 재시작 자동 재접속. **대리 로봇 검증** — 실기/WiFi 수치는 대기 ([E.15 R5](docs/plan/e15-real-robot.md)). 설치: [docs/robot-setup.ko.md](docs/robot-setup.ko.md). **신뢰 LAN 전용** — 평문 TCP, 인증/TLS 없음 |

구조적 한계 (버그가 아니라 설계):

- **낡은 브리지가 새 스택을 조용히 깨뜨린다 (KI-17).** 브리지를 켜둔 채 VM 시뮬
  스택을 재기동하면 죽은 스택의 라우트가 남아, 새 스택의 액션 하위 서비스가 맥에서
  디스커버리 안 된다(실측: 0/6 → 브리지 재시작 후 4/4). `rosmac sim`은 시작 시
  브리지 세션을 리셋해 이를 방지 — Nav2 풀스택도 기본 브리지로 동작한다(스코핑 불필요).
- **맥↔VM 모든 메시지가 브리지 홉 하나를 건넌다.** 개발·teleop·시각화엔 충분;
  고주파 폐루프 제어는 VM 안(또는 로봇 위)에서 완결할 것.
- **UDP ignore 규칙이 없는 *다른* lima VM이 맥 로컬 DDS 디스커버리를 조용히
  잠식할 수 있다** (KI-28). rosmac 자체 VM은 규칙 내장;
  처방은 [known-issues KI-28](docs/plan/known-issues.md).
- **VM은 헤드리스 (D2)** — 내부에 RViz2/GUI 없음; 시각화 경로는 맥의
  Foxglove (`rosmac viz`).

## 아키텍처·설계 결정

결정 로그와 리스크 레지스터: [PLAN.md](PLAN.md).
막히면 [docs/plan/known-issues.md](docs/plan/known-issues.md) — 이 도구의 토대인
실측 함정 30개 DB.

## 라이선스

[MIT](LICENSE)

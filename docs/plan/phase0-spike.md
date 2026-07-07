# Phase 0 — 기술 스파이크 (리스크 킬러)

> 목표: 코드를 쓰기 전에 아키텍처의 3대 가정을 실측으로 검증하고 go/no-go를 결정한다.
> 산출물: `docs/plan/phase0-results.md` (측정값·버전·로그 포함)
> 예상 소요: 반나절 ~ 1일 (다운로드 대기 포함)
> 원칙: 여기서 실패하는 게 Phase 1에서 실패하는 것보다 100배 싸다.

## 태스크 목록

| # | 태스크 | 검증하는 가정 | 블로킹 여부 |
|---|---|---|---|
| 0.1 | RoboStack Humble osx-arm64 스모크 테스트 | "맥 네이티브 L1 레이어가 실제로 돈다" | Phase 1의 conda 파트 블로킹 |
| 0.2 | Lima VM + apt ROS2 Humble 설치 | "VM 레이어가 문서 그대로 돈다" | Phase 1의 lima 파트 블로킹 |
| 0.3 | zenoh-bridge-ros2dds 왕복 검증 | "L4 브리지가 토픽/서비스/**액션**을 전달한다" | **아키텍처 전체 블로킹 (최우선)** |
| 0.4 | 결과 기록 + go/no-go 게이트 | — | Phase 1 착수 조건 |

병렬화: 0.1과 0.2는 독립 — 동시 진행 가능. 0.3은 둘 다 완료 후.

---

## 0.1 RoboStack Humble osx-arm64 스모크 테스트

### 목적
RoboStack이 광고하는 osx-arm64 지원이 **이 맥**(현재 macOS 버전)에서 실제로 동작하는지,
어떤 경고/버그가 있는지 확인하고 버전을 고정한다.

### 선행 조건
- Homebrew 설치됨 (`brew --version`)
- 디스크 여유 ≥ 10GB

### 수행 절차

1. micromamba 설치 (conda보다 가볍고 빠름):
   ```bash
   brew install micromamba
   # 셸 훅 초기화 (zsh)
   micromamba shell init -s zsh
   exec zsh
   ```

2. ROS env 생성 — 채널 순서 중요 (`conda-forge`가 먼저, 그다음 `robostack-humble`):
   ```bash
   micromamba create -n ros_env \
     -c conda-forge -c robostack-humble \
     ros-humble-desktop \
     compilers cmake pkg-config make ninja \
     colcon-common-extensions rosdep
   micromamba activate ros_env
   ```
   ⚠️ 채널 이름 주의: 문서에 따라 `robostack-staging`으로 안내하는 글이 있음(구버전).
   설치 시점에 https://robostack.github.io/GettingStarted.html 에서 현행 채널명 확인 후
   결과 리포트에 기록할 것.

3. 기본 통신 스모크:
   ```bash
   # 터미널 A
   micromamba activate ros_env && ros2 run demo_nodes_cpp talker
   # 터미널 B
   micromamba activate ros_env && ros2 run demo_nodes_py listener
   ```

4. GUI 스모크:
   ```bash
   rviz2          # 창이 뜨고 Grid가 렌더링되는가, 크래시 없이 1분 유지되는가
   ros2 run rqt_graph rqt_graph
   ```

5. colcon 빌드 스모크 (맥에서 개발 루프가 성립하는지):
   ```bash
   mkdir -p ~/rosmac_spike/src && cd ~/rosmac_spike
   ros2 pkg create --build-type ament_python spike_py_node --destination-directory src
   colcon build
   source install/setup.zsh   # zsh용 setup 파일 존재 여부도 확인 항목
   ```

6. MoveIt/브리지 관련 패키지 설치 가능 여부만 확인 (실행은 Phase 2):
   ```bash
   micromamba install -n ros_env -c conda-forge -c robostack-humble \
     ros-humble-moveit ros-humble-foxglove-bridge --dry-run
   ```

### 완료 기준 (AC)
- [ ] talker↔listener 메시지 교환 확인
- [ ] rviz2가 뜨고 1분 이상 크래시 없음 (완벽하지 않아도 됨 — D4에 따라 보조 도구)
- [ ] `colcon build` + `source install/setup.zsh` 성공
- [ ] `ros-humble-moveit`, `ros-humble-foxglove-bridge`가 osx-arm64에 존재함을 확인
- [ ] SIP 비활성화 **없이** 전부 동작 (csrutil 건드리지 않음)

### 기록할 것 (→ phase0-results.md)
- macOS 버전, micromamba 버전, 설치된 `ros-humble-desktop` 버전
- 설치 중 나온 경고 전문, 실패한 패키지 목록
- rviz2 이상 증상 (렌더링 아티팩트 등)

### 실패 시 대응
- 특정 패키지 dylib 로드 실패 → `otool -L <plugin>.dylib`로 깨진 링크 확인,
  해당 라이브러리 버전 핀 시도 (R2의 libprotobuf 사례 패턴). 핀 목록은 결과 리포트에 기록
  → 나중에 `rosmac doctor` 지문 DB가 됨.
- env 생성 자체가 실패 → 아키텍처 D7 재검토: "맥 네이티브 레이어 포기, VM 단독 모드"로
  PLAN.md 수정 후 진행 (프로젝트는 계속 성립함).

---

## 0.2 Lima VM + apt ROS2 Humble 설치

### 목적
Lima로 ARM64 Ubuntu 22.04 VM을 **스크립트만으로** 프로비저닝할 수 있는지,
Tier 1 표준 절차(apt)가 그대로 통하는지 검증한다. 여기서 만든 YAML이 Phase 1 자산의 원형이 된다.

### 선행 조건
- `brew install lima` (버전 기록)
- 디스크 여유 ≥ 30GB

### 수행 절차

1. 스파이크용 Lima 템플릿 작성 — `~/rosmac_spike/lima-rosmac.yaml`:
   ```yaml
   # ARM64 Ubuntu 22.04 (Jammy) — Humble Tier 1 플랫폼
   images:
     - location: "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-arm64.img"
       arch: "aarch64"
   cpus: 4
   memory: "8GiB"
   disk: "30GiB"
   mounts:
     - location: "~/rosmac_spike"
       writable: true
   portForwards:
     - guestPort: 7447   # zenoh
       hostPort: 7447
     - guestPort: 8765   # foxglove_bridge (Phase 2 대비 미리)
       hostPort: 8765
   provision:
     - mode: system
       script: |
         #!/bin/bash
         set -eux
         # --- docs.ros.org Humble 공식 설치 절차 그대로 ---
         apt-get update && apt-get install -y locales curl gnupg lsb-release
         locale-gen en_US en_US.UTF-8
         update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
         add-apt-repository -y universe
         curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
           -o /usr/share/keyrings/ros-archive-keyring.gpg
         echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
           > /etc/apt/sources.list.d/ros2.list
         # OSRF gazebo-stable 저장소 필수 — packages.ros.org의 libignition-sensors6(6.8.0)이
         # desktop-full 의존성(>=6.8.1)을 못 채워 apt가 깨짐 (Phase 0 실측, KI-13)
         curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
           -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
         echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
           > /etc/apt/sources.list.d/gazebo-stable.list
         apt-get update
         DEBIAN_FRONTEND=noninteractive apt-get install -y ros-humble-desktop-full ros-dev-tools
         echo "source /opt/ros/humble/setup.bash" >> /etc/skel/.bashrc
         echo "source /opt/ros/humble/setup.bash" >> /home/*/.bashrc || true
   ```
   ⚠️ ros.key 배포 방식이 apt 저장소 개편으로 바뀌었을 수 있음(2025년 GPG 키 로테이션 있었음).
   설치 실패 시 docs.ros.org 현행 절차와 대조하여 스크립트를 고치고 결과 리포트에 기록.

2. 기동 및 검증:
   ```bash
   limactl start --name=rosmac-spike ~/rosmac_spike/lima-rosmac.yaml
   limactl shell rosmac-spike -- bash -lc 'ros2 doctor'
   limactl shell rosmac-spike -- bash -lc 'ros2 run demo_nodes_cpp talker'
   ```

3. VM 내부 통신 스모크: talker(터미널1) + listener(터미널2), `ros2 topic hz /chatter`

4. 포트포워딩 검증 (0.3 준비):
   ```bash
   limactl shell rosmac-spike -- bash -lc 'python3 -m http.server 7447 --bind 0.0.0.0' &
   curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:7447 && echo " forward OK"
   ```

5. 프로비저닝 재현성 검증 — **한 번 지우고 처음부터 다시**:
   ```bash
   limactl delete -f rosmac-spike
   limactl start --name=rosmac-spike ~/rosmac_spike/lima-rosmac.yaml
   ```
   두 번째 기동이 사람 개입 0회로 성공해야 함 (Phase 1 `rosmac init`의 전제).

### 완료 기준 (AC)
- [ ] provision 스크립트만으로 (수동 개입 없이) `ros-humble-desktop-full` 설치 완료
- [ ] VM 내부 talker/listener 동작
- [ ] 호스트→VM 포트포워딩(7447) 확인
- [ ] 삭제 후 재생성이 무인으로 재현됨
- [ ] 기록: 프로비저닝 소요 시간, 디스크 사용량, lima 버전

### 실패 시 대응
- 이미지 URL 만료 → Ubuntu cloud-images에서 jammy arm64 현행 URL로 교체
- apt 키 문제 → 위 ⚠️ 참조
- Lima 자체 문제가 반복되면 → 폴백: `limactl start template://ubuntu-lts`로 24.04를 띄우고
  Humble 대신 소스 문제인지 분리 진단. 그래도 안 되면 D2 재검토(UTM + 수동 스크립트).

---

## 0.3 zenoh-bridge-ros2dds 왕복 검증 ★ 아키텍처 최대 리스크

### 목적
맥 네이티브 DDS ↔ VM DDS 간에 토픽/서비스/**액션**/파라미터가 투명하게 오가는지 검증.
MoveIt은 액션 헤비(`/move_action` 등)이므로 **액션이 안 되면 이 아키텍처는 기각**이다 (R1).

### 선행 조건
- 0.1, 0.2 완료
- zenoh-bridge-ros2dds 릴리스 바이너리 (https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds/releases)
  - 맥용: `*-aarch64-apple-darwin.zip` / VM용: `*-aarch64-unknown-linux-gnu.zip`
  - **양쪽 같은 버전**으로 받을 것. 버전을 결과 리포트에 기록 (Phase 1에서 이 버전을 핀).

### 수행 절차

1. 양측 공통 환경 원칙:
   ```bash
   export ROS_LOCALHOST_ONLY=1   # DDS를 각 호스트 안에 가둠 — 브리지만 경계 통과
   export ROS_DOMAIN_ID=0        # 양측 동일
   ```
   RMW는 우선 양측 기본값(fastrtps)으로 시작. 문제 발생 시 양측 모두
   `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`로 통일해 재시도 (변경 여부 기록).

2. 브리지 기동:
   ```bash
   # VM 측 (listen)
   limactl shell rosmac-spike -- bash -lc \
     'ROS_LOCALHOST_ONLY=1 ./zenoh-bridge-ros2dds -l tcp/0.0.0.0:7447'
   # 맥 측 (connect — lima 포트포워딩 경유)
   ROS_LOCALHOST_ONLY=1 ./zenoh-bridge-ros2dds -e tcp/127.0.0.1:7447
   ```

3. 검증 매트릭스 — 아래 표를 전부 채운다:

   | 테스트 | 명령 (요지) | 방향 | 통과 기준 |
   |---|---|---|---|
   | T1 토픽 VM→맥 | VM에서 talker, 맥에서 `ros2 topic echo /chatter` | VM→맥 | 메시지 수신, `ros2 topic hz` ≈ 1Hz |
   | T2 토픽 맥→VM | 반대 방향 | 맥→VM | 동일 |
   | T3 토픽 목록 가시성 | 맥에서 `ros2 topic list`에 VM 토픽 표시 | — | 표시됨 |
   | T4 서비스 | VM에서 `add_two_ints_server`, 맥에서 `ros2 service call` | 맥→VM | 올바른 합 반환 |
   | T5 **액션** | VM에서 `ros2 run action_tutorials_py fibonacci_action_server`, 맥에서 `ros2 action send_goal --feedback fibonacci ...` | 맥→VM | goal 수락 + **feedback 스트림 수신** + result 수신 |
   | T6 파라미터 | 맥에서 `ros2 param list/get` (VM 노드 대상) | 맥→VM | 조회 성공 |
   | T7 대역폭 | VM에서 1MB급 토픽 10Hz 발행(스크립트), 맥에서 `ros2 topic bw` | VM→맥 | ≥ 5MB/s 유지, 드랍 기록 (R4 데이터) |
   | T8 안정성 | T1 상태로 10분 방치 | — | 브리지 크래시/메모리 폭주 없음 |
   | T9 재연결 | 브리지 한쪽 kill 후 재기동 | — | 수동 개입 없이 토픽 재개 |

   T7용 발행 스크립트 (VM에서):
   ```bash
   ros2 topic pub -r 10 /bigdata std_msgs/msg/ByteMultiArray \
     "{data: [$(python3 -c 'print(",".join(["0"]*1000000))')]}"
   # 위 방식이 CLI 한계로 느리면 rclpy 5줄 스크립트로 대체 (결과 리포트에 스크립트 첨부)
   ```

4. QoS 엣지케이스 (MoveIt 대비):
   - transient_local(latched) 토픽: VM에서 `ros2 topic pub --qos-durability transient_local /desc std_msgs/String "data: x" -1` 후 맥에서 늦게 구독 → 수신되는가?
     (`/robot_description`이 이 패턴 — Phase 2에서 Foxglove가 URDF 받는 경로)

### 완료 기준 (AC)
- [ ] T1~T6 전부 통과 (**T5 액션 feedback 포함 — 최우선**)
- [ ] T7 대역폭 수치 기록 (통과/미달 무관하게 수치 자체가 산출물)
- [ ] T8, T9 통과
- [ ] transient_local 케이스 결과 기록
- [ ] 사용한 zenoh-bridge 버전 + RMW 조합 기록

### 실패 시 대응 (폴백 사다리)
1. RMW를 양측 cyclonedds로 통일 후 전체 재시도.
2. zenoh-bridge 설정 파일 모드(json5)로 전환, `queries_timeout` 등 조정.
3. 그래도 T5(액션) 실패 → **폴백 실행**: Fast DDS Discovery Server 방식 검증
   - VM: `fastdds discovery -i 0 -l 0.0.0.0 -p 11811` (+ lima 포트포워딩 11811 추가)
   - 양측: `export ROS_DISCOVERY_SERVER=127.0.0.1:11811`, `ROS_LOCALHOST_ONLY` 해제
   - 같은 매트릭스 T1~T9 재검증. 단, 이 방식은 디스커버리만 중앙화하고 데이터는
     DDS 직통이므로 VM 네트워크 모드를 lima의 `vzNAT`→소켓 네트워크로 바꿔야 할 수 있음
     (검증 결과에 따라 D3 갱신).
4. 둘 다 실패 → 아키텍처 축소: "VM 단독 모드 + Foxglove(8765 직결)"로 PLAN.md 수정.
   이 경우에도 rosmac의 가치(원커맨드 VM 관리 + doctor + 프리셋)는 유지됨.

---

## 0.4 결과 기록 + go/no-go 게이트

### 수행 절차
1. `docs/plan/phase0-results.md` 작성 — 템플릿:
   ```markdown
   # Phase 0 결과 (날짜)
   ## 환경: macOS x.y / 칩 / RAM / lima vX / micromamba vX
   ## 0.1 RoboStack: PASS|PARTIAL|FAIL — 버전표, 경고, 핀 목록
   ## 0.2 Lima VM:  PASS|FAIL — 프로비저닝 시간, 수정한 스크립트 diff
   ## 0.3 브리지:   T1..T9 표 + 수치, RMW/버전 조합, QoS 케이스
   ## 게이트 결정: GO | GO(수정안: ...) | NO-GO(대안: ...)
   ## PLAN.md 반영 사항: D3/D7 등 갱신 목록
   ```
2. PLAN.md의 결정 로그/리스크 레지스터를 실측 결과로 갱신.

### 게이트 기준
- **GO**: 0.1~0.3 AC 전부(또는 폴백 경로로) 충족 → Phase 1 착수
- **GO (수정)**: 일부 레이어 포기/교체가 필요하지만 프로젝트 성립 → PLAN.md 수정 후 착수
- **NO-GO**: 브리지·폴백 모두 실패 + VM 단독 모드도 가치 없다고 판단될 때만. (가능성 낮음)

게이트 판정은 에스컬레이션 대상이다 — 판정안을 근거와 함께 사용자에게 보고하고
승인 후 Phase 1로 넘어간다 (AGENTS.md 4절).

---

## 부록 A — 명령별 기대 출력 (판정 기준)

실제 출력이 아래와 **의미상** 일치하면 통과다 (숫자·타임스탬프 차이는 무시).
다르면 known-issues.md 검색부터.

**A1. talker/listener (0.1-3, 0.2-3 공통)**
```
[INFO] [<ts>] [talker]: Publishing: 'Hello World: 1'
[INFO] [<ts>] [listener]: I heard: [Hello World: 1]   ← listener 쪽. 번호가 계속 증가해야 함
```
판정: listener에 "I heard"가 2회 이상 연속 출력. 한 번도 안 나오면 통신 실패.

**A2. `ros2 doctor` (0.2-2)**
```
All <N> checks passed
```
경고(`UserWarning: ... network interface`)는 VM 환경에서 흔하며 WARN까지는 통과.
`Failed` 항목이 있으면 전문을 결과 리포트에 기록.

**A3. `limactl list --json` (0.2)** — 파싱 대상 필드:
```json
{"name":"rosmac-spike","status":"Running","arch":"aarch64", ...}
```
판정: `status == "Running"`, `arch == "aarch64"` (x86_64면 이미지 URL이 잘못된 것).

**A4. zenoh 브리지 기동 로그 (0.3-2)**
```
[<ts> INFO] zenoh-bridge-ros2dds vX.Y.Z
[<ts> INFO] ... Listening on tcp/0.0.0.0:7447        ← VM 측
[<ts> INFO] ... Connected to tcp/127.0.0.1:7447      ← 맥 측 (connect 성공 라인 필수)
```
판정: 맥 측 로그에 연결 성공 라인. `Connection refused` 반복이면 포트포워딩(0.2-4) 재점검.

**A5. 액션 테스트 T5 기대 출력 (맥 측)**
```
Waiting for an action server to become available...
Sending goal: order: 5
Goal accepted with ID: ...
Feedback: partial_sequence: [0, 1, 1]        ← feedback이 최소 1회 이상 스트림
Result: sequence: [0, 1, 1, 2, 3, 5]
Goal finished with status: SUCCEEDED
```
판정: **accepted + feedback ≥ 1회 + SUCCEEDED** 세 가지 전부. feedback 없이 result만
오면 "부분 통과"로 기록하고 R1 관련 조사 (MoveIt은 feedback 스트림에 의존).

**A6. `ros2 topic bw /bigdata` (T7)**
```
average: 9.87 MB/s
```
판정: 문서 기준 ≥ 5MB/s. 미달이어도 FAIL 아님 — 수치 기록이 산출물 (R4 대응 자료).

## 부록 B — zenoh-bridge 바이너리 획득 절차 (0.3 선행조건 상세)

```bash
# 1) 최신 릴리스 태그와 자산 목록 확인 (gh CLI 있으면):
gh release view --repo eclipse-zenoh/zenoh-plugin-ros2dds --json tagName,assets \
  --jq '.tagName, (.assets[].name)'
# gh 없으면:
curl -s https://api.github.com/repos/eclipse-zenoh/zenoh-plugin-ros2dds/releases/latest \
  | grep -E '"tag_name"|"name".*zip'

# 2) 자산 이름에서 다음 두 개를 고른다 (이름 패턴은 릴리스마다 조금씩 다름 — 목록에서 실물 확인):
#    - 맥용:  *aarch64-apple-darwin*.zip
#    - VM용:  *aarch64-unknown-linux-gnu*.zip
#    ⚠️ "standalone" / "plugin" 두 형태가 있으면 standalone(bridge 실행파일)을 받는다.

# 3) 다운로드 + sha256 기록 (결과 리포트에 붙여넣기):
shasum -a 256 <다운로드파일>

# 4) VM으로 전달은 마운트 경로 이용:
cp zenoh-bridge-ros2dds ~/rosmac_spike/   # VM에서 /Users/.../rosmac_spike 로 보임
limactl shell rosmac-spike -- bash -lc 'cp <mount>/zenoh-bridge-ros2dds ~/ && chmod +x ~/zenoh-bridge-ros2dds'
```

주의: 브리지의 메이저 버전과 문서의 플래그(`-l`, `-e`)가 달라졌을 수 있다.
`--help` 출력을 먼저 확인하고, 달라진 플래그는 문서를 고치고 기록한다.

## 부록 C — T7 대역폭 발행용 rclpy 스크립트 (CLI pub이 느릴 때)

`~/rosmac_spike/bigpub.py` (VM에서 `python3 bigpub.py`):
```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import ByteMultiArray

class BigPub(Node):
    def __init__(self):
        super().__init__('bigpub')
        self.pub = self.create_publisher(ByteMultiArray, '/bigdata', 10)
        self.msg = ByteMultiArray()
        self.msg.data = [bytes([0])] * 1_000_000   # ~1MB
        self.create_timer(0.1, self.tick)          # 10Hz
    def tick(self):
        self.pub.publish(self.msg)

rclpy.init(); rclpy.spin(BigPub())
```
ByteMultiArray 직렬화가 비효율적이면 `sensor_msgs/msg/Image`(1MB 더미)로 교체 가능 —
교체 시 스크립트를 결과 리포트에 첨부.

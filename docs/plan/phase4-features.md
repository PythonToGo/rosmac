# Phase 4 — 기능 보강 (실사용 갭 해소)

> 목표: 2026-07-07 실사용 세션(외부 ROS2 워크스페이스를 rosmac으로 빌드·실행)에서
> 실증된 4대 기능 갭을 해소한다. 이 갭들은 외부 사용자가 **자기 프로젝트를 가져오는
> 순간** 겪게 될 문제들이라, 제품화(Phase 5)·공개(Phase 6)의 전제 조건이다.
> 착수 조건: Phase 2 완료 (충족됨)
> E2E 성공 기준: "처음 보는 ROS2 워크스페이스"를 클론 → `rosmac deps`로 의존성 해결 →
> `rosmac shell`에서 플래그 없이 colcon 빌드 성공 → 문제가 생기면 `rosmac ps`로
> 상태 파악 → 맥에서 안 되는 패키지는 `rosmac push`로 VM 빌드 — 이 흐름이 문서만으로 됨.
> 예상 소요: 2~3주 (파트타임)

## ⚠️ 실행 에이전트 지침 (이 문서는 Fable 외 에이전트 수행을 전제로 작성됨)

- 시작 전에 `AGENTS.md` **전체**를 읽는다. 태스크 수행 프로토콜(4절)을 그대로 따른다.
- 이 문서의 모든 셸 예시는 **검증된 실측 명령**이다. 단, 버전·경로는 실행 시점에
  달라질 수 있으니 결과가 기대 출력과 다르면 known-issues.md 검색 → 실패 대응 순.
- ros2 CLI를 직접 실행할 때는 반드시 `rosmac shell` 안에서 하거나, 다음 env 5개를
  전부 주입한다 (하나라도 빠지면 KI-6/KI-23 재발):
  `ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=0 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  ROS_DISTRO=humble CYCLONEDDS_URI=file://$HOME/.rosmac/cyclonedds.xml`
- 모든 subprocess 호출에 **타임아웃을 건다**. ros2 데몬이 hang이면 CLI가 무한 대기한다
  (2026-07-07 실측) — 이것이 4.3이 존재하는 이유이며, 4.3 구현 자체가 이 함정에
  빠지면 안 된다.
- 코드 스타일: 기존 모듈(`conda.py`, `bridge.py`)의 패턴을 따른다 — 외부 호출은
  `_run`류 단일 지점 경유(테스트 mock 지점), 한국어 주석, pydantic Config.
- 커밋: `[P4.X] 요약`. 결과는 `docs/plan/phase4-results.md`에 (템플릿:
  `docs/plan/templates/`). 새 함정 발견 시 known-issues.md에 KI-27부터 추가.
- **유닛 테스트 필수**: 각 태스크의 순수 로직(파싱·매핑·판정)은 subprocess mock으로
  `tests/unit/`에 커버. 기존 테스트(15개)가 전부 계속 통과해야 한다
  (`.venv/bin/python -m pytest tests/ -q --ignore=tests/e2e`).

## 태스크 의존 그래프

```
4.1 빌드 마찰 제거(A1) ──┐
4.2 rosmac deps (A2) ────┼→ 4.5(=Phase 4 E2E) 외부 워크스페이스 시나리오 검증
4.3 rosmac ps (A3) ──────┤
4.4 rosmac push (A4) ────┘   ※ 4.4는 착수 전 D14 승인 필요 (에스컬레이션)
```

4.1~4.4는 상호 독립 — 어느 순서로 해도 된다. 4.4만 결정(D14) 게이트가 있다.

---

## 4.1 빌드 마찰 제거 — colcon 기본 플래그 주입 (A1)

### 배경 (왜 필요한가 — 실측 근거)
`cmake_minimum_required(VERSION 3.5)`처럼 낡은 최소 버전을 선언한 패키지는
conda/macOS에서 CMP0094(OLD) 때문에 파이썬을 못 찾고 죽는다 (KI-25, franka_msgs로
실증). 해결 플래그는 `-DCMAKE_POLICY_DEFAULT_CMP0094=NEW`이며 부작용이 없다
(신식 패키지에는 이미 NEW가 기본). 지금은 사용자가 에러를 보고 문서를 찾아
직접 플래그를 붙여야 한다 — 이걸 자동화한다.

### 설계 (구현 방법을 특정한다)
colcon은 환경변수 `COLCON_DEFAULTS_FILE`이 가리키는 YAML을 기본 인자로 읽는다
(기본값 `~/.colcon/defaults.yaml`). **사용자 글로벌 파일(`~/.colcon/`)을 건드리지
않고** (절대 규칙 2), rosmac 상태 디렉토리에 우리 파일을 두고 `rosmac shell` /
`run_in_env`가 env로 주입한다:

1. `src/rosmac/assets/colcon-defaults.yaml` 신규:
   ```yaml
   # rosmac이 주입하는 colcon 기본값 (rosmac shell 안에서만 적용)
   # KI-25: 구식 cmake_minimum_required(3.5) 패키지의 FindPython 실패 우회
   build:
     cmake-args:
       - "-DCMAKE_POLICY_DEFAULT_CMP0094=NEW"
   ```
2. `assets.py`(기존 `ensure_mac_cyclonedds` 패턴과 동일)에 `ensure_colcon_defaults()`
   추가 — `~/.rosmac/colcon-defaults.yaml`로 복사·경로 반환.
3. `conda.py:run_in_env`와 `cli.py:shell`의 env 주입 목록에
   `COLCON_DEFAULTS_FILE=<경로>` 추가.
4. 이스케이프 해치: 사용자가 자기 defaults를 쓰고 싶으면
   `~/.rosmac/config.yaml`에 `build.colcon_defaults: false` (Config에 필드 추가,
   false면 주입 생략). README·workflow.md 함정표에 한 줄 반영.

### 절차
1. **전제 검증 먼저** (계획 시점 가정 — 실측으로 확인하고 results에 기록):
   `rosmac shell` 안에서 `COLCON_DEFAULTS_FILE=/tmp/probe.yaml colcon build --help`
   실행 전에, probe.yaml에 고의로 깨진 YAML을 넣어 colcon이 그 파일을 읽는지 확인
   (읽으면 파싱 에러가 난다 — 이것이 "읽는다"의 증거). 안 읽으면 colcon 버전 확인 후
   대안(`--metas` 옵션 또는 셸 alias) 조사로 전환하고 문서를 고친다.
2. 위 설계 1~4 구현.
3. **레거시 픽스처 패키지** 작성 — `tests/fixtures/legacy_msgs/` (KI-25 재현체):
   - `package.xml`: format 3, name `legacy_msgs`, `<depend>std_msgs</depend>`,
     `<buildtool_depend>rosidl_default_generators</buildtool_depend>`,
     `<member_of_group>rosidl_interface_packages</member_of_group>`
   - `CMakeLists.txt` (전문):
     ```cmake
     cmake_minimum_required(VERSION 3.5)   # ← 의도적 구식 선언 (KI-25 트리거)
     project(legacy_msgs)
     find_package(ament_cmake REQUIRED)
     find_package(std_msgs REQUIRED)
     find_package(rosidl_default_generators REQUIRED)
     rosidl_generate_interfaces(${PROJECT_NAME} "msg/Legacy.msg" DEPENDENCIES std_msgs)
     ament_package()
     ```
   - `msg/Legacy.msg`: `int32 value`
4. 검증 (음성 대조군 포함 — 순서 중요):
   ```bash
   # (a) 주입 끄고 빌드 → KI-25 재현 (Could NOT find Python) 확인
   #     config.yaml: build.colcon_defaults: false 로 두고
   rosmac shell -c 'cd <픽스처 복사한 임시 ws> && colcon build'   # 실패해야 정상
   # (b) 주입 켜고(기본) 같은 빌드 → 성공해야 정상
   ```
   (a)가 실패하지 않으면 픽스처가 KI-25를 재현 못 하는 것 — cmake 버전(<4 핀)과
   CMakeLists를 재점검한다.

### 완료 기준 (AC)
- [ ] 전제 검증(절차 1) 결과가 phase4-results.md에 기록됨
- [ ] 음성 대조군(주입 off) 실패 + 주입 on 성공 — 둘 다 실제 출력 첨부
- [ ] `build.colcon_defaults: false` 옵트아웃 동작 확인
- [ ] 유닛 테스트: ensure_colcon_defaults 멱등성, run_in_env env 주입 여부 (mock)

### 실패 시 대응
- colcon이 COLCON_DEFAULTS_FILE을 안 읽음 → colcon-core 버전 기록 후
  `colcon build`를 감싸는 `rosmac build` 서브커맨드(인자 그대로 전달 + cmake-args
  덧붙임)로 설계 변경. 문서 수정 후 같은 AC로 검증.
- 픽스처가 재현 안 됨 → env의 cmake 버전 확인 (`cmake<4` 핀이 살아있는지, KI-25).

---

## 4.2 의존성 매퍼 — `rosmac deps` (A2)

### 배경 (실측 근거)
mac/conda에서 rosdep은 실질 동작하지 않는다. 실사용 세션에서 xacro 부재(KI-26)로
launch가 알 수 없는 에러로 죽었고, 원인 특정에 시간이 들었다. package.xml에 선언된
의존성을 RoboStack conda 패키지로 매핑·설치해주면 이 부류가 사라진다.

### 설계
새 모듈 `src/rosmac/deps.py` + `rosmac deps <ws경로>` 커맨드.

1. **수집**: `<ws>/src/**/package.xml`을 재귀 glob → `xml.etree.ElementTree`로 파싱.
   수집 태그: `depend`, `build_depend`, `build_export_depend`, `exec_depend`,
   `test_depend`, `buildtool_depend`. 텍스트를 strip해서 dep 이름 set 구성.
2. **자기 참조 제거**: 워크스페이스 안에 있는 패키지 이름(각 package.xml의
   `<name>`)은 대상에서 뺀다 (워크스페이스 내부 의존).
3. **매핑 규칙** (순서대로 첫 매칭 적용):
   | 규칙 | 예 |
   |---|---|
   | ① 특수 매핑 표에 있으면 그 값 | `eigen`→`eigen`, `python3-numpy`→`numpy`, `python3-yaml`→`pyyaml`, `python3-pytest`→`pytest`, `libboost-dev`→`boost-cpp`, `pybind11-dev`→`pybind11` |
   | ② `python3-<x>` → `<x>` | `python3-requests`→`requests` |
   | ③ 그 외 → `ros-humble-<이름의 _를 -로>` | `moveit_msgs`→`ros-humble-moveit-msgs` |
   특수 매핑 표는 `deps.py`에 dict 상수로 두고, 커버 못 하는 이름은 "unknown"
   버킷으로 분류해 사용자에게 보여준다 (조용히 틀린 패키지를 설치하지 않는다).
4. **상태 판정**: 설치 여부는 `micromamba list -n <env> --json` 1회 호출로 얻은
   설치 목록과 대조 (dep마다 호출 금지 — KI-15 락 경합). 미설치분은
   `micromamba repoquery search -c robostack-humble -c conda-forge <이름> --json`으로
   **채널에 존재하는지** 확인 (존재 안 하면 "unavailable" 버킷).
5. **출력**: rich 테이블 — installed / missing(설치 명령 제시) / unknown /
   unavailable 4버킷. `--install` 플래그면 missing을 한 번의
   `micromamba install -y -n <env> -c conda-forge -c robostack-humble <목록>`으로 설치.
   `--json` 플래그로 기계 판독 출력(4.5 E2E와 CI에서 사용).

### 절차
1. `deps.py` 구현 (파싱·매핑은 순수 함수로 분리 — 유닛 테스트 대상).
2. 픽스처 `tests/fixtures/deps_ws/`: 패키지 2개 —
   `alpha`(depend: `rclpy`, `xacro`, `beta`(내부), `eigen`, `없는패키지xyz`),
   `beta`(depend: `std_msgs`). 기대: beta 제외, xacro·rclpy·std_msgs → ros-humble-*,
   eigen → eigen, 없는패키지xyz → unknown 또는 unavailable.
3. 유닛 테스트: 매핑 규칙 표 전체 + 자기 참조 제거 + 태그 수집.
4. 실전 검증: 실제 외부 워크스페이스(예: `~/rcm_ws` 사본의 src에서 franka_description
   + impl 패키지)에 실행 — 출력이 실제 필요 패키지와 일치하는지 육안 대조 후 기록.

### 완료 기준 (AC)
- [ ] 픽스처 워크스페이스에서 4버킷 분류가 기대와 일치 (`--json` 출력 첨부)
- [ ] `--install`로 missing 실제 설치 → 재실행 시 all installed
- [ ] repoquery 존재 확인이 실제로 가짜 패키지를 unavailable로 분류
- [ ] 한계 문서화: **선언 안 된** 런타임 의존(FindExecutable류)은 못 잡는다 —
      README/workflow에 "빌드 전 `rosmac deps`" 워크플로와 함께 한계 명시

### 실패 시 대응
- `repoquery search`가 없거나 출력 형식이 다름 → `micromamba search`로 대체 시도,
  둘 다 안 되면 존재 확인 생략하고 설치 시점 에러를 그대로 보여주는 설계로 후퇴
  (버킷이 3개가 됨 — 문서 수정).
- 대형 ws에서 느림 → 파싱은 로컬이라 병목 아님. micromamba 호출이 2회를 넘지
  않는지 확인.

---

## 4.3 그래프·프로세스 관찰 — `rosmac ps` (A3)

### 배경 (실측 근거 — 2026-07-07 장애의 교훈)
실사용자가 겪은 복합 장애: ① ros2 데몬 hang → 모든 `ros2 topic echo/list`가 무한
대기 ② VM에 남은 sim 프리셋 토픽이 zenoh 브리지로 맥에 유입 → 같은 프레임 이름의
/tf 이중 발행 → 시각화가 튕김 ③ 맥 브리지가 VM 재시작 전의 낡은 라우트 보유
④ 과거 세션의 고아 프로세스 4개. 각각은 사소하지만 **합쳐지면 원인 특정에 전문가도
1시간**이 걸렸다. `rosmac ps` 하나로 전 상태가 보이게 한다.

### 설계 — 출력 명세 (이 형태를 목표로 구현)
```
rosmac ps
── 맥 ──────────────────────────────────────────
 zenoh-bridge   PID 89050  (기동 16:50, ~/.rosmac/run/bridge.pid 일치)
 ros2 daemon    PID 41099  응답 ✓ (XMLRPC 0.1s)
 ROS 노드 프로세스:
   49850 rcm_node          49853 joint_state_integrator   ...
 ⚠ pidfile 없는 zenoh-bridge 프로세스 1개 (고아 의심): PID 4132
── VM (rosmac) ─────────────────────────────────
 zenoh-bridge   active (systemd)   foxglove_bridge  inactive
 sim 세션: 없음
 ROS 프로세스: 없음
── 그래프 (핵심 토픽 발행자) ────────────────────
 /tf                  ⚠ 발행자 2 (rsp[맥], zenoh_bridge[=VM 유래])
 /joint_states        발행자 1 (joint_state_integrator)
 /robot_description   발행자 1 (rsp)
```

### 구현 지침 (함정 회피가 핵심 — 아래를 따르지 않으면 4.3 자체가 hang한다)
1. **데몬 응답성부터** 확인하고, 이후의 그래프 질의는 그 결과에 따라 분기:
   ```python
   # 실측 검증된 프로브 (2026-07-07): ros2 데몬 XMLRPC, 포트 = 11511 + ROS_DOMAIN_ID
   import socket, xmlrpc.client
   socket.setdefaulttimeout(5)
   proxy = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{11511 + domain_id}/ros2cli/")
   proxy.system.listMethods()   # 예외(TimeoutError 등) = hang/부재
   ```
   hang이면 그래프 절은 건너뛰고 "`ros2 daemon stop && ros2 daemon start`
   (rosmac shell 안에서) 또는 rosmac doctor --fix(Phase 5)" 처방을 출력.
2. 그래프 질의는 `ros2 topic list --no-daemon --spin-time 3`,
   발행자 조회는 `ros2 topic info <t> --verbose` — **모든 호출에
   subprocess timeout(15s)**. timeout 발생 = "그래프 질의 실패"로 표기하고 진행
   (전체 커맨드가 죽지 않는다).
3. 핵심 토픽 목록(고정): `/tf`, `/tf_static`, `/joint_states`, `/robot_description`,
   `/clock`. 발행자 2 이상 또는 zenoh_bridge가 발행자인데 로컬에도 동종 발행자가
   있으면 ⚠ (오늘의 이중 /tf 패턴).
4. 맥 프로세스 수집: `pgrep -fl`은 자기 매칭 함정(KI-18)이 있다 — 패턴에
   브래킷 트릭을 쓰지 말고 **수집 후 자기 PID·부모 PID를 제외**하는 방식으로.
   대상 패턴: `zenoh-bridge`, `ros2-daemon`, `--ros-args`(런치된 노드들의 공통 지문),
   `ros2 (launch|run|topic|action|bag)`.
5. VM 수집: `limactl shell <vm> -- bash -c 'ps aux'` 결과를 맥에서 필터
   (VM 안 grep의 인용 지옥 회피). VM 정지 상태면 그 절만 "VM stopped"로 표기.
   VM 셸은 ROS 소싱이 안 되어 있음을 잊지 말 것 (KI-19) — 단 ps에는 불필요.
6. tmux sim 세션: `tmux has-session -t rosmac-sim` (sim.py의 SESSION 상수 재사용).
7. `--json` 출력 지원 (doctor와 동일 패턴) — Phase 5 CI·report에서 재사용.

### 절차
1. `src/rosmac/psview.py` 구현 (`ps.py`는 표준 모듈명과 혼동 여지 — psview로),
   `cli.py`에 `rosmac ps` 등록.
2. 유닛 테스트: 발행자 수 판정 로직, 고아 판정(pidfile 불일치), 자기 PID 제외 (mock).
3. **실전 재현 검증** (오늘 장애의 축소판을 만들어 감지되는지):
   ```bash
   rosmac up && rosmac sim panda-moveit          # VM에서 /tf 발행 중
   rosmac shell -c 'ros2 run demo_nodes_cpp talker &'   # 맥 로컬 노드
   rosmac ps        # → VM 유래 토픽 + 맥 노드 + 브리지가 한 화면에
   rosmac sim stop && rosmac ps                  # → sim 잔재 사라짐 확인
   kill -STOP <데몬PID> && rosmac ps             # → "데몬 응답 없음" (hang 아님!)
   kill -CONT <데몬PID>
   ```

### 완료 기준 (AC)
- [ ] 데몬 SIGSTOP 상태에서 `rosmac ps`가 **15초 안에** 경고와 함께 완주 (hang 금지)
- [ ] 이중 /tf 시나리오(맥 rsp + VM sim 동시)에서 ⚠ 표시 실측
- [ ] 고아 브리지(pidfile 삭제 후) 감지 실측
- [ ] `--json` 스키마가 results에 기록됨

### 실패 시 대응
- `ros2 topic info`에 --no-daemon이 없어 데몬 의존 → 데몬 정상일 때만 발행자 절을
  출력하고, hang 시엔 토픽 목록(--no-daemon)까지만. 문서에 반영.
- pgrep 패턴이 과다 매칭 → 수집 결과에 화이트리스트 2차 필터 (cmdline에
  `--ros-args` 또는 알려진 바이너리 경로 포함).

---

## 4.4 VM 빌드 경로 — `rosmac push` (A4) ※ 착수 전 D14 승인 필요

### 배경 (실측 근거)
lima 템플릿에 `mounts:`가 없어 VM은 맥 파일시스템을 전혀 못 본다 (2026-07-07 확인).
libfranka 같은 **linux 전용 의존성** 패키지는 맥 빌드가 원천 불가 — 지금은 공식
탈출로가 없다 (실사용 세션에선 "빌드 제외"로 우회했음).

### D14 (제안 — 이 태스크 착수 전 사용자 승인, AGENTS 규칙 3)
**워크스페이스 전달 = push 복사 방식** (마운트 아님).
근거: ① 마운트 추가는 VM 재생성 필요(provision 변경, KI-24 고려) + virtiofs/9p
성능·안정성 미검증 ② 복사는 명시적이라 "VM 안 빌드 산출물이 맥 워크스페이스를
오염"하는 사고가 구조적으로 없음 ③ v0.2에서 마운트 재평가 여지 유지.
트레이드오프: 대형 ws는 복사 시간, 수정→재push 루프 필요 (문서에 명시).

### 설계
`rosmac push <ws경로> [--name <이름>] [--build]`:
1. 검증: `<ws>/src` 존재해야 함 (아니면 "colcon ws 루트를 지정" 안내, exit 2).
2. 전송: `src/`만 tar 파이프로 복사 (build/install/log 제외가 자동으로 달성됨):
   ```bash
   tar -C <ws>/src -cf - . | limactl shell <vm> -- \
     bash -c 'mkdir -p ~/rosmac-ws/<이름>/src && tar -C ~/rosmac-ws/<이름>/src -xf -'
   ```
   (`limactl copy -r`은 버전별 동작 편차가 보고됨 — tar 파이프가 이식성 안전.
   구현 전에 `limactl copy -r` 현행 버전 동작을 1회 확인하고 결과 기록 — 되면
   그쪽이 단순.) 재push는 기존 src를 지우고 다시 풀기 (VM쪽 `rm -rf` 대상은
   `~/rosmac-ws/<이름>/src` 고정 경로만 — 절대 규칙 7).
3. `--build`: VM에서 빌드까지 실행. **반드시 명시적 소싱** (KI-19):
   ```bash
   limactl shell <vm> -- bash -c \
     'source /opt/ros/humble/setup.bash && cd ~/rosmac-ws/<이름> && \
      colcon build --symlink-install 2>&1 | tail -30'
   ```
   apt 의존성은 자동 해결하지 않는다 — 실패 시 "VM은 표준 Ubuntu이므로
   `rosmac shell --vm` 후 `rosdep install --from-paths src -y`가 동작"을 안내
   (VM에선 rosdep이 진짜로 동작한다 — 맥과의 차이를 문서에 명확히).
4. 실행 안내 출력: `rosmac shell --vm` + `source ~/rosmac-ws/<이름>/install/setup.bash`.
   토픽은 zenoh 브리지로 맥에서 자동 가시 (기존 아키텍처 그대로).

### 절차
1. D14 에스컬레이션 → 승인 후 PLAN.md 결정 로그에서 "(제안)" 제거.
2. **linux 전용 픽스처** `tests/fixtures/linux_only_pkg/` (ament_cmake):
   ```cpp
   // src/epoll_node.cpp — 의도적으로 linux 전용 헤더 사용 (맥 빌드 불가 증명용)
   #include <sys/epoll.h>
   #include <cstdio>
   int main() { int fd = epoll_create1(0); std::printf("epoll fd=%d\n", fd); return 0; }
   ```
3. 음성 대조군: 맥 `rosmac shell`에서 이 픽스처 colcon build → `sys/epoll.h` 없음으로
   실패해야 정상 (출력 기록).
4. `rosmac push tests/fixtures/... --build` → VM 빌드 성공 → VM에서 실행:
   epoll fd가 0 이상이면 성공.
5. 실전급 검증(선택이지만 권장): franka_ros2 등 libfranka 의존 리포로 동일 흐름.

### 완료 기준 (AC)
- [ ] D14 승인 기록 (PLAN.md 갱신 커밋)
- [ ] 음성 대조군(맥 빌드 실패) + push 후 VM 빌드·실행 성공 — 출력 첨부
- [ ] 재push 시 이전 산출물이 새 빌드를 오염하지 않음 (파일 삭제 후 재push로 확인)
- [ ] `rosmac push` 없이 접근하던 기존 기능(sim 프리셋의 자산 push)과 충돌 없음
      (sim은 `~/rosmac-presets/`, push는 `~/rosmac-ws/` — 경로 분리 확인)

### 실패 시 대응
- tar 파이프가 limactl 셸 stdin을 못 탐 → 임시 파일 경유(`limactl copy` 단일 파일
  + VM에서 해제)로 후퇴. 성능 수치 기록.
- VM 디스크 부족 → `limactl shell -- df -h` 확인 후 사용자 보고 (VM 디스크 확장은
  스코프 밖 — known-issues에 추가만).

---

## 4.5 Phase 4 E2E — "외부 워크스페이스" 시나리오 (게이트)

### 절차 (tests/e2e/test_phase4.sh 로 스크립트화)
깨끗한 상태(`rosmac down` 후 `rosmac up`)에서:
1. 픽스처 3종(legacy_msgs, deps_ws, linux_only_pkg)을 임시 디렉토리에 복사해
   가짜 "외부 프로젝트" 구성.
2. `rosmac deps --json` → missing 검출 → `--install` → 재실행 all-installed.
3. `rosmac shell -c 'colcon build'` → legacy_msgs 포함 전부 플래그 없이 성공.
4. `rosmac ps --json` → 데몬 응답 ✓, 경고 0.
5. `rosmac push <linux_only> --build` → VM 빌드·실행 성공.
6. 정리(`rosmac down --keep-vm`) 후 잔여 프로세스 0 (`rosmac ps`로 확인 — dogfooding).

### 완료 기준 (AC)
- [ ] test_phase4.sh 무인 완주 (전 단계 exit 0), 소요 시간 기록
- [ ] phase4-results.md 작성 + PLAN.md 상태 라인 갱신

## 명시적 비목표
- rosdep 자체의 맥 지원 수리 (업스트림 규모)
- VM 마운트 방식 워크스페이스 공유 (D14 — v0.2 재평가)
- 선언되지 않은 런타임 의존성의 정적 탐지 (한계로 문서화)

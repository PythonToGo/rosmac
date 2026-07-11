# known-issues — 함정 DB (증상 → 원인 → 해결)

> 막히면 **이 파일에서 에러 메시지를 먼저 검색**한다.
> 새 함정을 해결하면 같은 형식으로 여기에 추가한다 (AGENTS.md 4절 프로토콜 6단계).
> [계획시점] 표시 = 리서치 기반 예상 항목으로 아직 이 프로젝트에서 실측 안 됨.
> 실측되면 표시를 지우고 실제 에러 전문/버전을 붙일 것.

---

## KI-1. RoboStack 채널명 혼동 [계획시점]
- **증상**: `micromamba create ... -c robostack-humble` 시 패키지를 못 찾음
  (`nothing provides ros-humble-desktop`)
- **원인**: RoboStack 채널이 시기에 따라 `robostack-staging` ↔ `robostack-humble`로
  바뀌어 왔고, 오래된 블로그 글들이 구채널을 안내함
- **해결**: https://robostack.github.io/GettingStarted.html 의 현행 설치 명령을 확인해
  그대로 사용. 확정된 채널명을 `phase0-results.md`와 `config.yaml` 기본값에 반영

## KI-2. RoboStack dylib 링크 깨짐 (플러그인 로드 실패) [계획시점]
- **증상**: 노드/플러그인 기동 시 `dlopen(...dylib): Library not loaded: @rpath/libprotobuf.X.dylib`
  류 에러. 대표 실사례: RoboStack ros-noetic#459 — Gazebo 플러그인이 구버전
  libprotobuf에 링크된 채 배포되어 dlopen 실패
- **원인**: conda-forge의 의존 라이브러리가 업데이트됐는데 RoboStack 패키지가
  구버전에 링크된 채로 남음
- **해결**: ① `otool -L <문제 dylib> | grep 'not found 후보'`로 깨진 링크 특정
  ② 해당 라이브러리를 요구 버전으로 핀: `micromamba install 'libprotobuf==<버전>'`
  ③ 핀을 `phase0-results.md`의 핀 목록과 doctor C9 지문 DB에 추가

## KI-3. ROS apt GPG 키 만료/로테이션 [계획시점]
- **증상**: VM 프로비저닝 중 `apt-get update`가
  `NO_PUBKEY` / `EXPKEYSIG` / `The following signatures couldn't be verified` 실패
- **원인**: ROS apt 저장소 GPG 키가 로테이션됨 (2025년에 실제 발생 이력)
- **해결**: docs.ros.org Humble 설치 페이지의 현행 키 설치 절차와
  `assets/provision/10-ros2-humble.sh`를 대조해 키 URL/방식 갱신.
  (최근 방식은 `ros2-apt-source` deb 패키지 설치로 바뀌었을 수 있음 — 문서 우선)

## KI-4. Ubuntu cloud image URL 404 [계획시점]
- **증상**: `limactl start`가 이미지 다운로드 단계에서 실패
- **원인**: `cloud-images.ubuntu.com/jammy/current/`의 파일명 변경 또는 EOL 이동
- **해결**: https://cloud-images.ubuntu.com/jammy/ 에서 arm64 `.img` 현행 경로 확인 후
  템플릿 교체. jammy가 EOL로 내려갔으면 release 아카이브 URL 사용. 교체 사실 기록

## KI-5. zenoh 브리지 이중 실행 → 토픽 중복/루프
- **증상**: `ros2 topic hz`가 기대의 2배, 또는 echo에 같은 메시지 2회
- **원인**: 맥 쪽 브리지 프로세스가 2개 (pidfile 무시하고 수동 기동했을 때)
- **해결**: `pgrep -f zenoh-bridge-ros2dds`로 전부 확인 후 1개만 남김.
  Phase 1 이후에는 반드시 `rosmac up`으로만 기동 (R6)

## KI-6. ROS_LOCALHOST_ONLY 누락 → 디스커버리 오염
- **증상**: 토픽이 "가끔" 보이거나, 같은 LAN의 다른 ROS 머신 토픽이 섞임
- **원인**: 한쪽에서 `ROS_LOCALHOST_ONLY=1`이 빠진 채 노드 실행 —
  DDS가 실네트워크 멀티캐스트로 새어나감
- **해결**: 양측 모든 ROS 프로세스(브리지 포함)에 env 확인.
  `rosmac shell`/systemd 유닛을 통해서만 실행하면 구조적으로 방지됨 (doctor C4)

## KI-7. transient_local 토픽이 브리지 건너에서 안 보임 [계획시점]
- **증상**: 맥에서 `/robot_description` 등 latched 토픽 echo가 영원히 대기
- **원인**: 브리지의 QoS 매핑이 durability를 보존하지 못하는 경우
- **해결**: ① zenoh-bridge 버전업 확인 ② Foxglove 경로는 영향 없음
  (foxglove_bridge는 VM 로컬 DDS 직결이므로 브리지를 안 거침 — phase2 2.1 설계 근거)
  ③ 맥 쪽에서 정말 필요하면 구독측 QoS를 transient_local로 명시:
  `ros2 topic echo /robot_description --qos-durability transient_local --qos-reliability reliable`

## KI-8. `ros2 topic list`에 상대편 토픽이 없음 (브리지는 살아 있음)
- **증상**: 브리지 프로세스 정상, 포트 연결 정상인데 토픽 미표시
- **원인 후보 순서대로**: ① ROS_DOMAIN_ID 불일치 ② 한쪽 브리지가 DDS를 못 봄
  (ROS_LOCALHOST_ONLY 없이 띄운 브리지 vs =1로 띄운 노드는 서로 다른 인터페이스에 있을 수 있음
  — **브리지와 노드의 env를 동일하게**) ③ ROS2 데몬 캐시 → `ros2 daemon stop && ros2 topic list`
- **해결**: doctor C4~C8 순서로 점검. C8(uuid 토픽 왕복)이 최종 판정

## KI-9. macOS에서 zsh + conda env의 setup 파일
- **증상**: `source install/setup.bash`가 zsh에서 미묘하게 깨짐 (complete 함수 에러 등)
- **원인**: 셸 불일치
- **해결**: zsh에서는 항상 `setup.zsh`를 소싱. 존재 여부는 Phase 0.1 AC에 포함됨

## KI-10. Lima mount 경로에서 colcon 빌드 느림/락 문제 [계획시점]
- **증상**: VM에서 맥 마운트 경로(`~/rosmac_spike` 등) 위 colcon build가 비정상적으로 느림
- **원인**: Lima 기본 마운트(reverse-sshfs/9p)의 I/O 성능 한계
- **해결**: VM 내 빌드는 VM 로컬 경로(`~/ws`)에서 수행. 마운트는 소스 열람/교환용으로만.
  (아키텍처상 VM에서 빌드할 일은 드묾 — 빌드는 맥 네이티브가 원칙)

## KI-11. Gazebo Fortress 명령어 혼동
- **증상**: `gz sim` 명령이 없음 (`command not found`)
- **원인**: Humble 페어링인 Fortress의 CLI는 `ign`(`ign gazebo -s -r world.sdf`).
  `gz sim`은 Garden 이후 명명. 블로그 글들이 자주 섞어 씀
- **해결**: Fortress에서는 `ign gazebo`, ros 패키지는 `ros-humble-ros-gz*` 사용.
  버전 조합을 바꾸지 말 것 (D8 — Harmonic 조합은 별도 검증 항목)

## KI-13. VM apt: ros-humble-desktop-full 의존성 충돌 (libignition-sensors6)
- **증상**: Lima provision 중 `apt-get install ros-humble-desktop-full`이
  `Depends: libignition-sensors6-* (>= 6.8.1) but 6.8.0-1~jammy is to be installed ...
  E: Unable to correct problems, you have held broken packages.`로 실패 (2026-07-07 실측)
- **원인**: packages.ros.org가 배포하는 Ignition Fortress 바이너리(6.8.0)가
  desktop-full 의존성 체인이 요구하는 6.8.1보다 낮음. 6.8.1+는
  packages.osrfoundation.org(gazebo-stable)에만 있음
- **해결**: provision에 OSRF 저장소 추가 (lima-rosmac.yaml에 반영됨):
  `curl -sSL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg`
  후 `deb ... http://packages.osrfoundation.org/gazebo/ubuntu-stable jammy main` 등록 → apt update

## KI-14. RoboStack osx-arm64: foxglove-bridge가 최신 빌드 세대에 없음
- **증상**: `micromamba install ros-humble-moveit ros-humble-foxglove-bridge --dry-run`이
  `Could not solve for environment specs` (ros2-distro-mutex 충돌 트리) 실패 (2026-07-07 실측)
- **원인**: 현재 env는 mutex 0.9.0 / `np2py312*_18` 세대인데, osx-arm64용
  `ros-humble-foxglove-bridge`는 `_13`(py311, mutex 0.8 세대) 빌드까지만 존재 —
  둘을 한 env에 못 넣음. moveit은 `_18` 빌드가 있어 단독 설치는 정상
- **해결**: 맥 env에 foxglove-bridge를 넣지 않는다. 아키텍처상 foxglove_bridge는
  **VM 쪽에서 실행**(phase2 2.1)이므로 영향 없음. 맥에서 정말 필요해지면
  env 세대를 낮추는 대신 VM apt판을 쓸 것

## KI-15. micromamba run 동시 실행 시 락 경합
- **증상**: `micromamba run -n ros_env ...` 2개를 동시에 띄우면
  `error libmamba Could not set lock (Resource temporarily unavailable)` (2026-07-07 실측)
- **원인**: micromamba가 `~/.cache/mamba/proc` 락을 프로세스마다 잡음
- **해결**: 동시 실행이 필요하면 `micromamba run` 대신 셸 훅 활성화 사용:
  `eval "$(micromamba shell hook -s zsh)" && micromamba activate ros_env` 후 일반 실행

## KI-16. fastrtps에서 브리지 경유 서비스 호출 무응답 (payload size 에러)
- **증상**: 맥→VM `ros2 service call`이 영원히 대기. VM 서버 stderr에
  `[RTPS_READER_HISTORY Error] Change payload size of '36' bytes is larger than
  the history payload size of '23' bytes and cannot be resized` (2026-07-07 실측)
- **원인**: Fast DDS(기본 RMW)의 리더 히스토리 프리얼록 버퍼가 zenoh 브리지가
  보낸 서비스 요청 페이로드보다 작아 수신 거부. 토픽은 되고 서비스만 죽는 지문
- **해결**: 양측 전부 `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`로 통일 (폴백 사다리 1단계).
  cyclonedds 전환 후 서비스/액션/파라미터 전부 정상. Phase 1 기본값으로 채택 권고
  (VM: `apt install ros-humble-rmw-cyclonedds-cpp`, 맥: 같은 이름 conda 패키지 `_18` 존재)

## KI-17. 브리지 비정상 종료 잔재로 토픽 2배 수신 (KI-5 변형)
- **증상**: `ros2 topic hz`가 정확히 2배(2.002Hz), echo에 같은 메시지 2회 —
  브리지 프로세스는 양쪽 1개씩뿐인데도 발생 (2026-07-07 실측)
- **원인**: 맥 브리지를 SIGKILL 등으로 죽였다 재기동하면, VM 브리지에 이전 세션의
  라우트가 남아 신규 세션과 이중 라우팅됨 (VM 브리지 로그에 "New ROS 2 bridge
  detected" 누적 3회 확인)
- **해결**: 양쪽 브리지를 모두 재기동해 세션 상태 초기화. Phase 1 `rosmac up/down`은
  브리지를 반드시 짝으로 관리하고 SIGTERM으로 정상 종료시킬 것 (R6 강화 근거)

## KI-18. 셸 래퍼에서 pkill -f 자기 매칭
- **증상**: `limactl shell vm -- bash -c 'pkill -f zenoh-bridge; ...'`가 exit 255,
  후속 명령 미실행 (2026-07-07 실측, 3회 재현)
- **원인**: `bash -c`의 커맨드라인 자체에 패턴 문자열이 포함돼 pkill이 자기 셸을 죽임
- **해결**: 패턴에 문자 클래스 사용(`pkill -f "bigpub[.]py"`), comm 매칭(`pkill zenoh`),
  또는 kill 명령을 별도 셸 호출로 분리

## KI-19. VM에서 `bash -lc`가 ROS env를 못 받음 (.bashrc early-return)
- **증상**: `limactl shell ... bash -lc 'ros2 ...'`가 `ros2: No such file or directory`
  — 프로비저닝이 .bashrc에 source 라인을 넣었는데도 (2026-07-07 실측, Phase 1)
- **원인**: Ubuntu 기본 `.bashrc` 상단의 비인터랙티브 early-return(`case $- in *i*)`)
  때문에 끝에 추가된 `source /opt/ros/humble/setup.bash`에 도달하지 못함.
  인터랙티브 셸(`rosmac shell --vm`)은 정상
- **해결**: 프로그램적 VM 명령은 항상 `source /opt/ros/humble/setup.bash`를 명시.
  Phase 0 스파이크가 우연히 전부 명시했어서 그때는 안 드러났음

## KI-20. 고아 맥 브리지 → 새 브리지가 포트 충돌로 즉사 (KI-5/R6 변형)
- **증상**: `rosmac up`은 성공처럼 보이는데 doctor C6 FAIL(실행 중 아님) + C8은 PASS.
  브리지 로그 끝에 `Unable to open listener tcp/[::]:7447 ... Address already in use
  ... Exiting` (2026-07-07 실측, Phase 1 E2E)
- **원인**: pidfile 없이 도는 고아 브리지(수동 기동/판일 삭제)가 router 모드의
  listen 포트 [::]:7447을 점유 → 새 브리지가 기동 직후 종료. 트래픽은 고아가
  처리하므로 통신은 되는 척 함 — 관리 불능 상태
- **해결**: ① bridge.start()가 스폰 1.5s 후 생존 확인, 즉사 시 로그 tail과 함께 에러
  ② bridge.stop()이 pidfile 밖 고아(pgrep -f 경로)도 SIGTERM 정리
  ③ 진단은 doctor C6(pidfile) + 로그의 "Address already in use" 지문

## KI-21. foxglove_bridge 3.4.x의 웹소켓 서브프로토콜이 foxglove.sdk.v1로 변경
- **증상**: `foxglove.websocket.v1`로 접속하는 스크립트/구클라이언트가
  `HTTP 400 — Missing expected sec-websocket-protocol header`로 거부됨.
  브리지 로그엔 `foxglove::websocket::server] Dropping client ...: handshake failed`
  (2026-07-07 실측, ros-humble-foxglove-bridge 3.4.2)
- **원인**: 3.4.x부터 Rust Foxglove SDK 기반 서버로 재작성 — 서브프로토콜이
  `foxglove.sdk.v1`. 에러 메시지가 "header 없음"이라 오진하기 쉬움 (헤더는 있고 값이 다름)
- **해결**: 스크립트 접속 시 subprotocols=["foxglove.sdk.v1"]. Foxglove 데스크톱 앱(신버전)은
  자동 협상하므로 영향 없음
- **여담**: foxglove-bridge systemd 유닛에 `HOME` env 필수 — 없으면 rcl_logging이
  "Failed to get logging directory"로 즉사 (30-foxglove.sh에 반영됨)

## KI-22. ament_python 실행 파일이 bin/에 설치돼 `ros2 run`이 못 찾음
- **증상**: colcon build 성공 후 `ros2 run <pkg> <exe>` → `No executable found`.
  실행 파일이 `install/<pkg>/bin/`에 있음 (`lib/<pkg>/`가 아니라) (2026-07-07 실측, py312 env)
- **원인**: 최신 setuptools가 스크립트를 bin/에 설치. ros2 run은 lib/<pkg>/만 봄 (상류 이슈)
- **해결**: 패키지에 setup.cfg 추가:
  `[develop] script_dir=$base/lib/<pkg>` + `[install] install_scripts=$base/lib/<pkg>`
  (examples/pick_demo/setup.cfg 참조)

## KI-23. CycloneDDS 참가자 10개 제한 → spawner 등 노드가 조용히 죽음
- **증상**: 노드 로그에 `Failed to find a free participant index for domain 0` +
  `rmw_create_node: failed to create domain` — MoveIt 스택에서 panda_arm_controller
  spawner만 실패해 goal이 error_code=-4(CONTROL_FAILED)로 즉시 반환 (2026-07-07 실측)
- **원인**: ROS_LOCALHOST_ONLY=1 → lo는 멀티캐스트 불가 → CycloneDDS가 유니캐스트
  디스커버리로 폴백 → 참가자 인덱스 필요 → 기본 MaxAutoParticipantIndex=9라
  **호스트당 DDS 참가자 10개 제한**. 브리지 2개+MoveIt 노드 7개+CLI로 초과
- **해결**: CycloneDDS 설정으로 상한 확장 (assets/cyclonedds.xml, MaxAutoParticipantIndex=120).
  VM은 /etc/cyclonedds.xml + systemd 유닛/프로파일에 CYCLONEDDS_URI, 맥은
  ~/.rosmac/cyclonedds.xml — rosmac이 모든 실행 경로(run_in_env/bridge/shell/sim)에 주입
- **지문**: 액션 goal이 "Solution found but controller failed during execution"과 함께
  수십 ms 만에 실패하면 이것부터 의심
- **⚠️ 변형 (P2.7 실측, 진단에 2시간 소요)**: 설정이 **일부 프로세스에만** 적용되면
  더 악랄한 부분 가시성이 생긴다 — Max=9인 프로세스는 인덱스 10+ 참가자를
  **영원히 발견 못 함** (SPDP 유니캐스트를 자기 상한까지만 쏨). 증상: 토픽 일부는
  되는데 서비스/액션만 무응답, 참가자 수·기동 순서에 따라 성공/실패가 오락가락.
  VM 재부팅 후 zenoh-bridge 유닛에 CYCLONEDDS_URI가 빠져 있던 것이 원인이었음.
  **점검법**: `cat /proc/$(pgrep -x zenoh-bridge-ro)/environ | tr '\0' '\n' | grep CYCLONE`
  — 모든 ROS/DDS 프로세스(systemd 유닛 포함)가 동일 설정을 가져야 한다

## KI-24. lima provision 스크립트는 **매 부팅마다 재실행** — VM 내 수동 수정이 증발
- **증상**: VM 안에서 고친 systemd 유닛/설정이 재부팅 후 원상복구됨.
  실측: zenoh-bridge 유닛에 넣은 CYCLONEDDS_URI가 재부팅마다 사라져
  KI-23 변형(서비스/액션 무응답)이 재발 — 두 번이나 같은 원인으로 디버깅함 (P2.7)
- **원인**: lima의 `provision: mode: system` 스크립트는 cloud-init **per-boot**로
  등록됨 (1회성 아님!). 부팅마다 VM "생성 시점"의 스크립트가 다시 돌아
  유닛 파일을 덮어씀. 스크립트 원본은 `~/.lima/<vm>/lima.yaml` (인스턴스 사본) —
  리포의 템플릿을 고쳐도 기존 VM에는 반영 안 됨
- **해결**: ① 영구 수정은 반드시 provision 스크립트(리포 asset)에 반영하고
  VM 재생성, 또는 ② 기존 VM 유지 시 `~/.lima/<vm>/lima.yaml`의 provision도 함께 패치
  ③ VM 내 수동 유닛 수정은 임시조치일 뿐임을 기억
- **지문**: "재부팅 후에만 뭔가 되돌아간다" → 무조건 이것

## KI-25. 구식 `cmake_minimum_required(VERSION 3.5)` 패키지가 맥 RoboStack에서 FindPython 실패
- **증상**: 메시지 패키지(rosidl) colcon 빌드가
  `Could NOT find Python (missing: Python_EXECUTABLE ... NumPy ...)` 로 실패.
  python/numpy/헤더는 env에 전부 있는데도 (2026-07-07 실측, franka_msgs·franka_ros2 v2.2.0)
- **원인**: 해당 패키지의 `cmake_minimum_required(VERSION 3.5)`가 CMake 정책을
  구버전 세트로 고정 → CMP0094(OLD)의 VERSION 우선 탐색이 conda(macOS) python을
  못 찾음. cmake 4.x에선 다른 에러(FindPythonInterp 제거)로 먼저 죽음 — cmake<4 핀 필요
- **해결**: ① env에 `cmake<4` 유지 (Phase 0 env 생성 목록에 반영: `'cmake<4'`)
  ② 소스 수정 없는 우회: `colcon build --cmake-args -DCMAKE_POLICY_DEFAULT_CMP0094=NEW`
  (또는 `-DPython_EXECUTABLE=$CONDA_PREFIX/bin/python3.12`)
- **지문**: 순수 rclcpp 패키지는 빌드되는데 .msg/.srv/.action 있는 패키지만 죽으면 이것

## KI-26. RoboStack `ros-humble-desktop`에 xacro 미포함 → launch가 알 수 없는 에러로 죽음
- **증상**: `ros2 launch ...` 가
  `executable '[<launch.substitutions.text_substitution.TextSubstitution object at 0x...>]' not found on the PATH`
  로 즉사. 에러 문구에 실행 파일 이름 대신 substitution 객체 repr이 찍혀 원인 특정이 어려움 (2026-07-07 실측)
- **원인**: launch 파일의 `Command([FindExecutable(name='xacro'), ...])` 패턴(URDF 생성 관례)에서
  xacro 부재. apt의 desktop과 달리 RoboStack `ros-humble-desktop` 메타패키지에는 xacro가 없음
- **해결**: env 생성 목록에 `ros-humble-xacro` 포함 (conda.py ENV_PACKAGES 반영).
  기존 env는 `micromamba install -n ros_env -c conda-forge -c robostack-humble ros-humble-xacro`
- **지문**: launch 에러에 `TextSubstitution object ... not found on the PATH` → FindExecutable 대상이 env에 없는 것

## KI-27. lima가 VM의 DDS UDP 포트를 자동 포워딩 → 맥 로컬 DDS 디스커버리 파괴
- **증상**: 맥 로컬 DDS 참가자끼리 일부만 서로 보임. 저인덱스 참가자(먼저 뜬 브리지 등)가
  발견 불능. VM 쪽 DDS 참가자 수에 따라 **간헐 발현** — "어제는 됐는데 오늘 안 됨"
  (2026-07-08 실측)
- **원인**: lima hostagent는 게스트가 listen하는 포트를 자동으로 맥 127.0.0.1에
  포워딩한다. VM DDS의 유니캐스트 포트(UDP 7410+2i)가 포워딩되면 limactl 소켓이
  맥 DDS의 SPDP 핑(127.0.0.1:7410~)을 가로채 VM으로 흘려보낸다
- **진단**: `lsof -nP -iUDP | grep limactl | grep ':74'` — limactl이 74xx를 쥐고 있으면 이것
- **해결**: lima 템플릿 portForwards 최상단에 UDP 전면 차단 규칙 2개
  (`guestPortRange: [1,65535], proto: udp, ignore: true` + 동일 규칙에 `guestIP: "0.0.0.0"`).
  **규칙 2개 다 필요** (게스트가 0.0.0.0에 bind한 경우 기본 규칙이 안 맞음 — 실측).
  기존 VM은 `~/.lima/<vm>/lima.yaml`에도 반영(KI-24) 후 VM 재시작
- **지문**: rosmac 경계는 TCP뿐(zenoh 7447, foxglove 8765) — UDP 포워딩은 어떤 경우에도 불필요

## KI-28. [원인 확정 2026-07-09] 맥 로컬 DDS 디스커버리 간헐 붕괴 — lima UDP 특정주소 하이잭
> 2026-07-08 2차 조사로 문제의 정의가 바뀜 — "브리지 고장"이 아니라 **macOS 호스트
> 전체의 lo0 멀티캐스트 디스커버리 신뢰성 문제**이고 브리지는 첫 피해자였을 뿐.
> 같은 날 3차 조사(재부팅 후)로 재정의 — "참가자 수에 따라 점진 붕괴"는 **반증**
> (누적 64개·churn 600회 전부 정상). 최유력 NECP로 재발 대기.
> **2026-07-09 4차 조사(자연 재발, E.15 R1 중)로 원인 확정 — 아래 4차 절 참조.**
> NECP 가설 반증. 진범: UDP ignore 규칙 없는 lima VM의 hostagent 포트포워딩.

- **4차 조사 (실측 2026-07-09, 자연 재발 — 원자료 `~/rosmac_spike/ki28/recur1/`)**:
  ⑭ E.15 R1 실측 중 재발 관측: 18:10 브리지 경유 echo 정상 → 로봇 스택(브리지·
     talker·서버·bigpub) 순차 기동 → 18:22 신규 참가자 쌍부터 실패, doctor C8 FAIL.
     **점진 악화 곡선이 "게스트 UDP 소켓 증가"와 정확히 동행**
  ⑮ 플레이북 ① 실행 결과 **limactl hostagent(UDP ignore 규칙 없는 rosmac-spike VM)가
     호스트 127.0.0.1:7410-7416+를 바인드** — 게스트에서 DDS 프로세스가 UDP 소켓을
     열 때마다 lima가 호스트에 특정주소+SO_REUSEADDR로 자동 포워드 바인드
     (⑪의 바인드 매트릭스에서 "허용" 확인된 바로 그 조합 — EADDRINUSE 없이 조용함)
  ⑯ 메커니즘: XNU는 127.0.0.1 목적지 데이터그램을 와일드카드(*:74xx, DDS)보다
     **특정주소(127.0.0.1:74xx, limactl) 소켓에 우선 배달** → ROS_LOCALHOST_ONLY=1인
     맥 DDS의 유니캐스트 전량(SEDP·데이터)이 74xx에서 잠식. SPDP(멀티캐스트
     239.255.0.1:7400)는 살아 있어 "일부 쌍만 실패" 비대칭(②↔④) 그대로 재현
  ⑰ **반증 실험 성공**: 하이재커 VM `limactl stop`만으로 맥 pub/echo 쌍 즉시
     복구(1.6s) — **무재부팅**. "재부팅 리셋"의 본질은 재부팅에 딸린 VM 정지였음.
     NECP였다면 VM 정지로 복구될 이유 없음 → NECP/LNP 가설 반증
  ⑱ 수리 검증: 제품 코드 `doctor.ensure_udp_ignore_rules()`를 해당 VM lima.yaml에
     적용 → VM 재기동 → 게스트 DDS 4프로세스 풀가동에도 호스트 74xx 바인드 0건,
     전 측정 정상. 2차 조사 ⑤의 유니캐스트 실패, ⑥ "KI-27 수정 후에도 지속"도
     당시 미수리 VM(hostagent가 구 설정 유지) 탓으로 정합 설명됨
  ⑲ 잔여 오염 처방: 하이잭 구간에 생성된 CLI 참가자·ros2 데몬은 하이잭 제거 후에도
     오염 상태 유지 → **좀비 kill + `ros2 daemon stop`으로 C8 PASS 복귀** (무재부팅)

- **증상**: 맥 로컬 DDS 참가자 간 디스커버리가 일부 쌍에서만 성립. 처음엔 브리지만
  소외("어제는 됐는데 오늘 안 됨")였다가, 세션 중 참가자가 누적될수록 CLI↔CLI까지
  실패로 **점진 악화** (같은 명령이 오전엔 성공, 오후엔 실패 — 실측).
  zenoh 세션(TCP)은 정상이라 `rosmac up`의 "브리지 상호 감지"는 통과함 (가짜 안심)
- **확인된 사실 (실측 2026-07-08)**:
  ① 맥에서 rmw/브리지 모두 **lo0 멀티캐스트(239.255.0.1:7400)로 SPDP** 사용
     (macOS lo0는 멀티캐스트 가능 — VM의 lo와 다름. KI-23의 유니캐스트 서사는 VM 한정)
  ② 파이썬 관찰자 소켓(같은 그룹 join)은 브리지 SPDP를 수신 — **브리지 송신은 정상**
  ③ 브리지도 CLI pub을 발견한 사례 있음(declares 기록) — **브리지 수신도 기능함**
  ④ 그런데 특정 쌍(브리지↔CLI, 나중엔 CLI↔CLI)은 몇 분을 기다려도 상호 발견 실패
  ⑤ `AllowMulticast=false`(+명시적 `<Peers>127.0.0.1`) 유니캐스트 전환 시도 →
     **맥에서는 CLI↔CLI조차 불성립** (pub 생존 확인된 유효 실측). Linux(VM)와 달리
     macOS에서 유니캐스트 인덱스 디스커버리가 동작하지 않는 것으로 보임 — 원인 미상
  ⑥ KI-27(lima UDP 하이잭) 수정 후에도 지속. 방화벽 off, 샌드박스 무관, lima
     하이잭 잔재 없음. 맥 무재부팅 3.8일
- **3차 조사 (실측 2026-07-08, 맥 재부팅 후 — 스크립트·원자료 `~/rosmac_spike/ki28/`)**:
  ⑦ 재부팅 직후 최소 구성(브리지+VM talker+맥 echo) 즉시 성공 —
     **"재부팅으로 리셋되는 커널/호스트 상태" 확정** (2차 조사 ① 전반부 완료)
  ⑧ **참가자 누적은 재발 조건 아님**: ddsperf(lo0 멀티캐스트, CLI와 동일 조건)를
     8개씩 64개까지 누적, 매 라운드 신선한 pub/echo 프로브 → **전 라운드 PASS**
     (지연 2~3초, 7400 바인더 66개에서도 정상)
  ⑨ **churn도 재발 조건 아님**: 상주 64개 위에 단명 참가자 600회 생성·소멸 +
     3연속 최종 프로브 → **전부 PASS**, 커널 undelivered/filtered 카운터 내내 0
  ⑩ **유니캐스트 전환(⑤) 복권**: 깨끗한 호스트에서 `AllowMulticast=false` +
     `<Peers>127.0.0.1` CLI↔CLI **성공(1.4초)** — 2차 조사 ⑤의 실패는 오염 상태
     아티팩트였음. 준비된 설정: `~/.rosmac/cyclonedds-unicast-ki28.xml`
     (주의: rmw_cyclonedds#376 — introspection 임시 참가자 디스커버리 제약 보고 있음)
  ⑪ **비-REUSE 하이잭 메커니즘 배제**: XNU `udp_input()`은 REUSE 없는 소켓에 배달 후
     루프를 `break`하지만(후순위 소켓 기아), 실측상 (a) DDS 생존 중엔 비-REUSE 바인드가
     EADDRINUSE로 불가, (b) 하이재커가 선점하면 새 참가자는 조용한 부분 디스커버리가
     아니라 **노드 생성 하드 실패**(`failed to bind to ANY:7400` → rmw 에러) —
     어제는 노드가 잘 뜨고 디스커버리만 안 됐으므로 이 메커니즘 아님.
     부수 수확: 7400 바인드 매트릭스 실측(비-REUSE·REUSEADDR-only 와일드카드는 거부,
     REUSEPORT는 허용, 특정주소+REUSEADDR 허용)
  ⑫ 브리지의 lo0 고정은 보장된 동작(bridge.py가 `ROS_LOCALHOST_ONLY=1` 주입,
     `netstat -g`로 239.255.0.1 멤버십 lo0 단독 확인) — 인터페이스 불일치 가설 약화
  ⑬ 업스트림 검색: macOS lo0 멀티캐스트 디스커버리 붕괴의 공개 보고 **없음**
     (cyclonedds·ROS 트래커 전수). 이 현상은 미보고로 보임
- **유력 가설 (3차 조사 후 갱신)**: 참가자 수·churn·바인드 순서가 아니라
  **macOS Local Network Privacy(NECP)의 소켓별 수신 차단**이 최유력 —
  XNU `udp_input()`의 `necp_socket_is_allowed_to_send_recv_v4()`가 소켓 단위로
  멀티캐스트 배달을 스킵하는 유일한 정책 경로이고, "파이썬 관찰자는 수신하는데 특정
  프로세스만 못 받는" 비대칭(②↔④), 시간 경과 재발, 재부팅 리셋과 모두 정합.
  macOS 15+에서 유사 증상 보고 다수(sACN 멀티캐스트 간헐 고장, LNP 토글로 일시 해복,
  매일 재발 — Apple Community 256051137, Dev Forums 764523: spawn 체인이 끊긴
  프로세스는 LNP가 조용히 차단)
- **재발 시 플레이북 (증상 관찰 즉시, 재부팅 전에 순서대로 수집)**:
  ① `lsof -nP -iUDP:7400` — 바인더 전수 (비정상 바인더 유무)
  ② `netstat -g` — 239.255.0.1 멤버십이 lo0 외 인터페이스에 있는지
  ③ `netstat -s -p udp` — filtered/undelivered 멀티캐스트 카운터
  ④ 유니캐스트 프로브: `CYCLONEDDS_URI=file://~/.rosmac/cyclonedds-unicast-ki28.xml`로
    pub/echo 쌍 — 이게 되면 "멀티캐스트 경로만 고장" 확정
  ⑤ **시스템 설정 > 개인정보 보호 및 보안 > 로컬 네트워크** — 터미널/관련 항목 토글 후
    재프로브. 이걸로 복구되면 NECP/LNP 원인 확정 (핵심 판별 실험)
  ⑥ 위 결과를 이 KI에 추가하고 재부팅
- **처방 (4차 조사로 확정, 무재부팅)**: ① `lsof -nP -iUDP:7400-7440`에서 limactl 등
  DDS 외 프로세스의 127.0.0.1:74xx 특정주소 바인드 확인 ② 해당 lima VM의 lima.yaml에
  UDP ignore 규칙 적용(`doctor.ensure_udp_ignore_rules`) 후 VM 재시작(또는 정지)
  ③ 하이잭 구간에 생긴 hang CLI 프로세스 kill + `ros2 daemon stop` ④ doctor C8 확인.
  rosmac 자체 VM은 KI-27 수정으로 안전 — 위험은 **규칙 없는 외부/구 lima VM**.
  제품 대응 완료(E.16, 2026-07-09): **doctor C17**이 ①을 자동화 — limactl 특정주소 바인드
  FAIL + 위 처방 안내(--fix 비대상: 외부 VM 설정은 임의 수정하지 않음). C8 처방 문구에 ③ 반영
- **영향**: 브리지 경유 기능(sim 헬스체크, 맥↔VM 토픽, Foxglove의 맥 노드 데이터)
  간헐 마비. VM 내부 작업·맥 로컬 빌드·`rosmac push`는 무영향

## KI-29. `rosmac shell -c`로 맥 백그라운드 프로세스 기동 시 호출이 블록될 수 있음
- **증상**: `rosmac shell -c 'nohup ros2 topic pub … >/log 2>&1 & true'`가 즉시
  반환되지 않고 run_in_env의 300s 타임아웃까지 hang → TimeoutExpired traceback.
  이때 nohup 손자 프로세스는 wrapper가 죽어도 **살아남아** 좀비 발행자가 됨
  (2026-07-08 실측: C14 양성 테스트 중 /tf pub이 정확히 이 패턴)
- **원인(추정)**: `micromamba run`이 자식 bash 종료 후에도 프로세스 그룹 종료를
  대기하는 것으로 보임. 같은 패턴이 블록 없이 동작한 사례도 있어(KI-28 정량화
  스크립트) 발동 조건 미상 — micromamba 락/버전 상태 의존 추정
- **우회**: 맥 쪽 백그라운드 프로세스가 필요하면 ① `rosmac shell`(인터랙티브) 안에서
  띄우거나 ② VM이면 `rosmac shell --vm -c`(limactl 경유라 무관) ③ 스크립트라면
  rosmac 밖에서 env를 직접 조립해 setsid로 기동. 정리는 `pkill -f <패턴>`으로
- **영향**: 자동화 스크립트/에이전트가 이 패턴을 쓰면 5분 hang + 좀비 프로세스.
  rosmac 자체 코드는 이 패턴을 쓰지 않음 (doctor C8은 limactl 직접 Popen)

## KI-12. Foxglove가 URDF 메시 파일을 못 찾음 [계획시점]
- **증상**: 3D 패널에 로봇이 흰 박스/빈 상태로 표시, 콘솔에 `package://` URL 해석 실패
- **원인**: URDF의 `package://` 메시 경로를 Foxglove(맥)가 로컬에서 해석 못 함
- **해결**: foxglove_bridge의 asset 서빙 기능(`/robot_description` + asset fetch) 활성 확인.
  안 되면 해당 메시 패키지를 맥 RoboStack env에도 설치해 Foxglove의
  ROS_PACKAGE_PATH 설정으로 해석시키는 방법을 검증 후 문서화

## KI-30. 대형 스택(nav2 등)의 서비스·액션이 무스코프 브리지에서 라우팅 실패
- **증상** (2026-07-11 실측, E.17 N2): 맥에서 `/navigate_to_pose` 액션 goal 전송이
  `wait_for_server`에서 90초에도 `SERVER_NOT_AVAILABLE`. 일반 서비스 호출
  (`/bt_navigator/get_parameters`)도 무한 대기. 반면 **토픽은 정상**(맥에서
  `/scan`·`/odom`·`/map` 수신 OK). `ros2 action info`엔 서버가 보이나 액션 하위
  **서비스**(`/navigate_to_pose/_action/send_goal` 등)가 맥에 프록시 안 생김
  (하위 토픽 feedback/status는 생김).
- **원인**: nav2 풀스택 = 서비스 **174개** + 액션 12개. 무스코프
  zenoh-bridge-ros2dds가 이 전부를 zenoh로 내보내 **맥 쪽 DDS 디스커버리를
  포화**시킴. 서비스(요청/응답 매칭)가 토픽보다 먼저 무너짐. cyclonedds·RMW·
  브리지 자체는 정상 — **순수 엔티티 수 문제**. 판별: nav2 전부 내리고 VM에
  `add_two_ints_server` 단독 기동 시 맥 서비스 호출 `sum=42` **즉시 성공**.
  (P0.3 단일 talker·P2.3 moveit ~40서비스는 통과 → 임계 ~40~174 사이.)
- **해결**: VM 브리지를 `-c <config.json5>`로 기동하고 `plugins.ros2dds.allow`에
  **필요한 인터페이스만 화이트리스트**. nav goal은 `action_servers:
  ["/navigate_to_pose"]` + 필수 pub/sub 토픽(/scan /odom /map /tf /plan
  /cmd_vel /goal_pose …) + `service_servers/clients: []`. nav2 노드 간 내부
  서비스는 VM 로컬 DDS라 스코핑과 무관(항법 정상). 스코핑 후 맥 goal 3/3
  SUCCEEDED. 브리지 로그에 `Route Action Server (ROS:/navigate_to_pose <->
  Zenoh:...) created` 확인.
- **영향/미해결**: rosmac 기본 브리지는 무스코프라 대형 스택 프리셋(nav2)을
  맥 네이티브 goal로 지원하려면 브리지 스코핑 도입이 전제 — 아키텍처 결정(D3
  인접) 필요. panda-moveit·gazebo-diffbot 등 기존 소형 프리셋은 무스코프로
  계속 동작(임계 미만). 스파이크 config: `~/rosmac_spike/nav2/bridge_scoped.json5`.

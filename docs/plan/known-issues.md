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

## KI-12. Foxglove가 URDF 메시 파일을 못 찾음 [계획시점]
- **증상**: 3D 패널에 로봇이 흰 박스/빈 상태로 표시, 콘솔에 `package://` URL 해석 실패
- **원인**: URDF의 `package://` 메시 경로를 Foxglove(맥)가 로컬에서 해석 못 함
- **해결**: foxglove_bridge의 asset 서빙 기능(`/robot_description` + asset fetch) 활성 확인.
  안 되면 해당 메시 패키지를 맥 RoboStack env에도 설치해 Foxglove의
  ROS_PACKAGE_PATH 설정으로 해석시키는 방법을 검증 후 문서화

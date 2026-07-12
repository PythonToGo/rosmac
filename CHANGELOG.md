# Changelog

이 프로젝트의 주요 변경 사항을 기록한다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/),
버전은 [SemVer](https://semver.org/lang/ko/)를 따른다 (D12).
**0.y.z 동안은 마이너 버전이 breaking change를 포함할 수 있다.**

## [0.1.0] - Unreleased

첫 공개 준비 버전 — Phase 0~4의 소급 요약.

### Added
- 코어 CLI: `init`(conda env·브리지·VM 프로비저닝, 멱등) / `up`·`down`·`status` /
  `doctor`(C1~C11 진단 + 처방, `--json`) / `shell`(ROS env 주입, `--vm`, `-c`) /
  `version` (Phase 1)
- 시뮬레이션: `sim panda-moveit`·`sim gazebo-diffbot` 프리셋(tmux 기동 + health 판정),
  `viz`(foxglove_bridge + 앱 딥링크) (Phase 2)
- 외부 워크스페이스 수용: `deps`(package.xml → RoboStack 설치, rosdep 대체) /
  `ps`(맥+VM 프로세스·토픽 발행자 관찰) / `push`(VM 전송 +`--build`) /
  colcon 빌드 기본값 자동 주입(구식 CMake 함정 우회) (Phase 4)
- 아키텍처: 맥 네이티브 개발(RoboStack) ↔ zenoh 브리지(TCP 7447) ↔
  Lima VM Ubuntu 22.04 arm64(MoveIt·Gazebo) ↔ Foxglove(ws 8765),
  양측 rmw_cyclonedds_cpp 고정 (D9)
- 함정 DB: 실측 known issues 30건 (`docs/plan/known-issues.md`)
- 진단·제보: `doctor --fix`(안전 항목 자동 수리), `report`(진단 번들 tar.gz,
  `~/.rosmac` 밖 수집 금지) (Phase 5)
- **실로봇 연결 (beta)**: `robot:` config 섹션 — 맥 브리지가 로봇 쪽
  zenoh 브리지로 TCP 엔드포인트 추가 (D15, 신규 커맨드 없음). up 도달성·
  드리프트 경고, status/ps robot link 표시, doctor C16 진단, report 로봇
  호스트 마스킹, 설치 가이드 `docs/robot-setup.md`. 대리 로봇(제2 VM) 실측
  검증 — 실기/WiFi 검증 전까지 "beta (surrogate-verified)" (E.15 R0~R4·R6)
- 브리지 능력 매트릭스: topics/services/actions/parameters/rosbag 실측 후
  README 기재 — parameters는 부분 지원(원시 서비스만, `ros2 param` CLI 불가),
  VM bag 회수는 `limactl cp` (D16), 구조적 한계 3종 명시 (E.14)
- 업그레이드 경로: 버전/sha 핀을 config에 동결하지 않음(커스텀 핀만 보존) +
  `up`/`init`이 브리지 바이너리 버전을 비교해 자동 갱신 — pip 업그레이드만으로
  신 핀 반영 (E.7)
- **Nav2 프리셋 (`sim nav2-diffbot`)**: Gazebo diffbot + gpu_lidar + slam_toolbox
  + Nav2(풀스택, 기본 브리지), 맥에서 `/navigate_to_pose` goal 3/3 SUCCEEDED.
  `rosmac sim`이 시작 시 브리지 세션을 리셋해 이전 스택 라우트 잔재로 인한 액션
  디스커버리 실패를 방지(KI-17). launch 신뢰성 stagger 타이밍. `viz --layout nav2`.
- **프리셋 `mac_env_pkgs`**: 맥에서 액션 goal을 보내는 데 필요한 msg 패키지를
  `rosmac sim`이 맥 conda env에 자동 설치(멱등, `deps.ensure_installed`). nav2는
  nav2_msgs — 없으면 goal이 "server not available"로 조용히 실패하던 함정 제거.
  (E.17/E.20)

### 실측 검증 (Phase 0/2/4 게이트)
- 브리지 대역폭 10.3 MB/s (1MB@10Hz 무손실), MoveGroup 액션 왕복 3연속 SUCCEEDED
- Gazebo Fortress headless RTF 1.00 (물리) / 0.99 (카메라 320x240@15Hz)
- 외부 워크스페이스 E2E (deps→빌드→ps→push) 무인 완주 38초

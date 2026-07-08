# Phase 4 결과 리포트 (진행 중)

> 시작: 2026-07-08. 환경: M3 Pro / macOS 26.x / ros_env(RoboStack humble, cmake 3.31.8) /
> colcon-defaults 0.2.9 / lima 2.1.4 / zenoh-bridge 1.9.0

## P4.1 — colcon 기본 플래그 주입 (2026-07-08)

### 전제 검증 (계획 절차 1)
colcon이 `COLCON_DEFAULTS_FILE`을 읽는지 — 고의로 깨진 YAML을 지정:
- `COLCON_DEFAULTS_FILE=<broken>.yaml colcon --help` → **즉시 파싱 traceback** (읽는다는 증거)
- 미지정 시 정상 help. `colcon-defaults 0.2.9` 설치 확인 → **전제 성립**

### 구현
- `assets/colcon-defaults.yaml` (CMP0094=NEW) + `assets.ensure_colcon_defaults()`
  → `~/.rosmac/colcon-defaults.yaml` (내용 불일치 시 갱신하는 멱등 쓰기)
- `conda.ros_env_pairs(cfg)` 신설 — rosmac 주입 env의 **단일 소스** (KI-6 5종 + KI-25 1종).
  `run_in_env`·`cli.shell`(인터랙티브 zshrc)이 공용
- 옵트아웃: `config.yaml`의 `build.colcon_defaults: false` (pydantic `BuildConfig`)

### AC 실측
| AC | 결과 |
|---|---|
| 전제 검증 기록 | ✅ 위 참조 |
| 음성 대조군 (주입 off, 픽스처 `tests/fixtures/legacy_msgs`) | ✅ `Could NOT find Python (missing: Python_EXECUTABLE ...)` → `Failed <<< legacy_msgs [4.07s]` |
| 양성 (rosmac shell, 주입 on) | ✅ `Summary: 1 package finished [5.77s]` |
| 옵트아웃 | ✅ `build.colcon_defaults: false` → `$COLCON_DEFAULTS_FILE` 빈 값 + KI-25 재발(grep 1건) 확인, 복원 후 재주입 확인 |
| 유닛 테스트 | ✅ `tests/unit/test_colcon_defaults.py` 4건 — 총 19 passed |

## P4.2 — rosmac deps (2026-07-08)

### 구현
- `src/rosmac/deps.py`: 수집(`scan_workspace` — DEP_TAGS 6종, 깨진 XML은 broken_xml로
  보고) → 매핑(`map_dep`: ①SPECIAL_MAP ②python3-접두 제거 ③ROS 관례명 →
  `ros-humble-<->`, 하이픈 포함 미등록 이름은 None=unknown — 틀린 이름을 지어내지
  않음) → 판정(installed: `micromamba list --json` 1회 / 가용성: `repoquery search
  --json`의 `result.pkgs`, 실측 확인) → `DepsReport` 6필드
- CLI: `rosmac deps <ws> [--install] [--json]`. src/ 없으면 exit 2.
  `--json`일 때 stdout은 JSON만 (진행 메시지 억제 — 파이프 안전)

### AC 실측
| AC | 결과 |
|---|---|
| 픽스처 4버킷 분류 (`tests/fixtures/deps_ws`) | ✅ installed 5 / missing 0 / unknown `libweird-system-dev` / unavailable `ros-humble-totally-fake-ros-pkg-xyz` / 내부 `alpha,beta` 제외. 소요 2.9s |
| `--install` 실동작 | ✅ `topic_tools` 선언 ws → missing `ros-humble-topic-tools` 검출 → 설치 → 재분석 missing 0 |
| 가짜 패키지 unavailable 분류 | ✅ repoquery pkgs=0 → unavailable |
| 한계 문서화 | ✅ workflow.md (선언된 의존성만 — FindExecutable류는 doctor 영역) |
| 유닛 테스트 | ✅ `test_deps.py` 4건 — 총 23 passed |

**실전 검증 (~/rcm_ws)**: installed 20종 정확 분류 + ws 내부 3패키지 제외 +
**실제 미설치 의존성 `ros-humble-joint-state-publisher-gui` 발견** (수동 지원
세션에서 놓쳤던 것 — 도구가 사람보다 나은 첫 사례).

## P4.3 — rosmac ps (2026-07-08)

### 구현
- `src/rosmac/psview.py` + `rosmac ps [--json]`. 데몬 응답성 XMLRPC 프로브(5s 컷,
  포트 11511+domain) 선행 → 결과에 따라 그래프 질의 분기. 전 외부 호출 타임아웃.
  맥 프로세스는 `ps -axo` 수집 후 자기/부모 PID 제외(KI-18 회피), VM은 단일
  `lima.shell` 합성 명령(units+tmux+ps). 핵심 토픽 5종의 발행자를
  `topic info --verbose`의 Publisher 섹션에서만 추출, 이중 발행 경고
  (`zenoh_bridge`/`_CREATED_BY_BARE_DDS_APP_` = 브리지 유래 마커, 실측)

### AC 실측
| AC | 결과 |
|---|---|
| 데몬 SIGSTOP에서 15초 내 완주 | ✅ 5.40s 완주 + "응답 없음(hang)" 경고 + 처방 출력 |
| 이중 발행 경고 | ✅ /tf 로컬 발행자 2개 구성에서 ⚠ 발화. 브리지 유래 케이스는 KI-28로 브리지 정지 상태라 마커 로직은 유닛으로 검증 |
| 고아 브리지 감지 | ✅ pidfile 제거 시나리오에서 "⚠ 고아 브리지 PID ..." |
| --json 스키마 | ✅ PsReport (daemon/bridge_pid/orphan_bridges/mac_nodes/vm_*/core_topics/warnings) |
| 유닛 테스트 | ✅ test_psview.py 4건 — 총 27 passed |

### 부산물: 실제 장애 2건 발견 (도구의 존재 이유 증명)
- **KI-27 (해결)**: lima의 UDP 자동 포워딩이 VM DDS 포트(7410~)를 맥 127.0.0.1에
  선점 → 맥 로컬 SPDP 핑을 가로챔. 템플릿+인스턴스 lima.yaml에 UDP 차단 규칙 2개
  추가로 해결 (`lsof`로 0건 확인)
- **KI-28 (미해결, 에스컬레이션)**: 맥 zenoh-bridge가 SPDP를 아예 송신하지 않아
  로컬 DDS와 양방향 불통 (CycloneDDS 트레이스 실측). 5가지 접근 실패 — 상세·다음
  가설은 known-issues.md. **P4.5 E2E의 브리지 경유 단계가 이것에 차단됨**

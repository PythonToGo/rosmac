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

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

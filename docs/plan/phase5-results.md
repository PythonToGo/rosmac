# Phase 5 결과 리포트 — 진행 중

> 시작: 2026-07-08. 환경: M3 Pro / macOS 26.x / python 3.12.9 / lima 2.1.4 /
> zenoh-bridge 1.9.0. KI-28은 재발 대기(플레이북 수록) 상태로 병행 관찰.

## P5.1 — 지원 매트릭스·버전 정책 (2026-07-08)

### 구현
- **버전 단일 소스**: pyproject의 `version` 하드코딩 제거 → `dynamic = ["version"]`
  + `[tool.hatch.version] path = "src/rosmac/__init__.py"`. `__version__`이 유일한 소스
- `rosmac --version` 플래그 추가 (typer eager callback) — 기존 `rosmac version`
  서브커맨드는 유지
- README: 지원 매트릭스 표 (HW: Apple Silicon M1+/Intel 명시적 비지원,
  OS: macOS 14+/실측 26.x, Python 3.11+/실측 3.12, ROS: Humble+cyclonedds 고정)
  + SemVer(D12)·0.y.z breaking 가능 명시 + CHANGELOG 링크
- `CHANGELOG.md` 생성 (Keep a Changelog) — Phase 0~4를 `[0.1.0] - Unreleased`로 소급

### AC 실측
| AC | 결과 |
|---|---|
| `rosmac --version`이 pyproject 버전과 일치 (단일 소스 테스트 포함) | ✅ `rosmac 0.1.0` = `importlib.metadata.version` = `__version__`. `tests/unit/test_version.py` 4건: 플래그·서브커맨드 출력, pyproject 하드코딩 부재+hatch path 검증, SemVer 형식 |
| README 지원 매트릭스 표 | ✅ "지원 매트릭스" 절 |
| CHANGELOG.md 존재 + CONTRIBUTING에서 참조 가능한 형태 | ✅ Keep a Changelog/SemVer 규약을 문서 서두에 명시 (Phase 6에서 링크만 하면 됨) |

## P5.2 — CLI 견고성 ③④: uninstall·부분 초기화 방어 (2026-07-08 완료 → P5.2 전체 완료)

### 구현
- `rosmac uninstall [--yes]`: 맥 브리지·ros2 데몬 정리 → conda env → VM → `~/.rosmac`
  순서로 제거. 각 대상을 경로/명령과 함께 출력, 개별 y/n 확인(절대 규칙 7), `--yes` 일괄.
  brew 도구·Foxglove 앱·리포는 안내만 (rosmac 소유 아님). `conda.remove_env` 신설
- 부분 초기화 방어(④): conda `_check`가 libmamba "prefix does not exist" 원문을
  "RoboStack conda env가 없습니다" + 처방 `rosmac init`으로 번역 — shell/deps/sim 전체 커버
- sim 사전점검 패널의 처방 중복 제거 (순서 보존 dedup)

### AC 실측 (실기 제거→재설치 완주)
| AC | 결과 |
|---|---|
| `uninstall --yes` 후 잔재 0 | ✅ `~/.rosmac` 없음 / `micromamba env list`에 ros_env 없음 / `limactl list`에 rosmac 없음 (rosmac-spike는 대상 아님) |
| 직후 `rosmac init` 완전 재설치 | ✅ 의존성 0.0s / env 생성 139.8s / 브리지 1.4s / VM 프로비저닝 176.1s (캐시 warm). `rosmac up` → doctor FAIL 0 → VM talker→맥 echo 왕복 수신 |
| (④ 방어) init 전 up/sim/shell | ✅ 셋 다 "처방: rosmac init" 패널 + exit 1 |
| (유닛) | ✅ test_uninstall.py 3건(순서·확인 스킵·깨끗한 상태) — 총 40 passed, ruff/mypy clean |

### 실측 중 발견·수정
- **ros2 데몬이 SIGTERM 무시하고 생존** → uninstall 후 삭제된 env를 참조하는 좀비 잔재.
  `_kill_ros2_daemon`을 SIGKILL로 변경 (데몬은 무상태 캐시라 안전)
- **프레시 설치 직후 doctor C8 일시 FAIL 2회** (첫 ros2 호출 콜드 스타트: 데몬 기동 +
  첫 zenoh 라우트 수립이 40s 창 초과 추정). 수동 왕복 성공 후 C8 단독·전체 doctor 모두
  PASS. 재현 시 "doctor 재실행" 처방이면 충분하나, 반복되면 C8 타임아웃 상향 검토
- 사용자 실행 참고: auto 권한 모드에서 uninstall 같은 파괴 명령은 에이전트가 실행 불가
  (분류기 거부) — 실측 시 사용자가 직접 실행했음

## P5.2 — CLI 견고성 ①②: exit code·non-TTY (완료)

### 구현 (2026-07-08)
- `errors.py` 신설: `RosmacError`(exit 1, message+hint) / `UsageError`(exit 2).
  **RuntimeError 상속** — psview 등의 `except RuntimeError` 방어선 유지가 목적
- 진입점을 `cli.main()`으로 교체(pyproject scripts): RosmacError → rich 패널
  (원인 escape + 처방), exit_code 그대로. 예상 밖 예외만 traceback + report 안내
- 전 모듈 `raise RuntimeError` → `RosmacError` 전환 (bridge/conda/lima/sim/cli),
  `ConfigError`는 `UsageError`(exit 2)로 재부모화
- cli 핸들러의 red-print+Exit 패턴 정리. **exit code 변경점**: viz 잘못된 레이아웃
  1→2 (사용법 오류로 재분류)
- README에 exit code 표(0/1/2) + 규약 설명 추가

### AC 실측
| AC | 결과 |
|---|---|
| exit code 표 문서화 + 시나리오 3개 실측 일치 | ✅ 잘못된 프리셋 `sim no-such-preset`→**2**(패널+`sim list` 처방) / env 없음(HOME 격리)→**1** / 정지된 VM `shell --vm`→**1**(limactl 원인 그대로 패널) |
| `rosmac status \| cat` · `TERM=dumb rosmac doctor` | ✅ rich 자동 폴백, 둘 다 exit 0 (doctor C1~C11 전 PASS 상태에서) |
| (유닛) | ✅ test_errors.py 6건 — 계층·main() exit code·CLI UsageError 2종. 총 37 passed, ruff/mypy clean |

- 미진한 점 (Run B로): env 없음 패널이 libmamba 원문 그대로 — ④부분 초기화 방어에서
  "rosmac init 먼저" 한 줄 안내로 다듬을 것

### 부수 작업 — 개발 도구 드리프트 정리
`.venv` 재생성(KI-28 조사 중 소실 발견)으로 dev 도구가 최신(ruff 0.15.20,
mypy 2.2.0)으로 올라오면서 기존 코드가 걸림 — P5.4(CI)에서 어차피 터질 것을 선정리:
- `ruff format` 전면 적용 (10파일, 기계적), F541 1건(cli.py f-string), mypy 1건
  (psview.py `out` 변수 str/str|None 재사용 → `info`로 분리)
- 유닛 31 passed / ruff check·format clean / mypy clean
- **주의**: dev deps가 하한 핀(`>=`)뿐이라 도구 메이저 업마다 재발 가능 —
  P5.4에서 CI 도구 버전 고정 여부 결정 필요

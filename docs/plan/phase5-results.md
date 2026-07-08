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

### 부수 작업 — 개발 도구 드리프트 정리
`.venv` 재생성(KI-28 조사 중 소실 발견)으로 dev 도구가 최신(ruff 0.15.20,
mypy 2.2.0)으로 올라오면서 기존 코드가 걸림 — P5.4(CI)에서 어차피 터질 것을 선정리:
- `ruff format` 전면 적용 (10파일, 기계적), F541 1건(cli.py f-string), mypy 1건
  (psview.py `out` 변수 str/str|None 재사용 → `info`로 분리)
- 유닛 31 passed / ruff check·format clean / mypy clean
- **주의**: dev deps가 하한 핀(`>=`)뿐이라 도구 메이저 업마다 재발 가능 —
  P5.4에서 CI 도구 버전 고정 여부 결정 필요

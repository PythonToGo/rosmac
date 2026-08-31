# Phase 6 결과 리포트 — 진행 중 (착수 2026-08-31)

> 주의: Phase 5.5(패키징·배포)·5.6(프레시 머신 게이트) 미완 상태에서 Phase 6
> **커뮤니티 인프라(6.3) 초안만 선작업**. 공개 행위(repo public, 태그, 포스팅)는
> 5.6 게이트 통과 후 사용자가 실행 (AGENTS.md 규칙 9).

## 0. 실행 환경
- macOS: 26.x / Apple Silicon
- 실행 에이전트: Claude (claude-sonnet-5), 2026-08-31
- 도구 버전: 변경 없음 (문서 작업)

## 태스크별 기록

### P6.3 커뮤니티 인프라 — PARTIAL (초안 작성)

작성한 파일 (전부 영어, D11):

| 파일 | 상태 | 비고 |
|---|---|---|
| `CONTRIBUTING.md` | 초안 | dev 셋업(.venv, `.[dev]`), CI 4체크 + 스모크, e2e 로컬 절차, 커밋 규약, pitfall 기여 형식, 스코프/비목표, MIT·CLA 없음 |
| `CODE_OF_CONDUCT.md` | 초안 | Contributor Covenant 2.1 원문. 연락처 `pythontogoplease@gmail.com` — **프로젝트 전용 alias로 교체 검토 필요** |
| `SECURITY.md` | 초안 | GitHub private advisory 1순위 + 이메일 폴백. 지원 버전 정책. **위협 모델 절**: zenoh 7447 평문·로봇 링크 평문 LAN 전용·바이너리 sha 핀·report 번들 수집 범위 |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | 초안 | `rosmac report` 번들 첨부 필수 체크박스. doctor 출력·버전·repro 필수 |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | 초안 | 스코프 가드(Humble/Apple Silicon), 아키텍처 결정 되돌리기는 Discussions로 |
| `.github/ISSUE_TEMPLATE/config.yml` | 초안 | blank 이슈 비활성, Discussions·troubleshooting·security advisory 링크 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 초안 | CI 체크리스트, CHANGELOG 갱신, 영어 문자열, 다운로드 핀+sha, pitfall 형식 |

관련 문서(6.1/6.4 선작업):

| 파일 | 상태 | 비고 |
|---|---|---|
| `docs/troubleshooting.md` | 초안 | 영어 사용자용. KI-1/6/16/17/19/22/23/24/25/26/27/28 + 데몬 hang + foxglove 서브프로토콜을 "증상(에러 원문)→원인 1줄→해결 명령" 형식으로. 내부 known-issues.md 링크 |
| `docs/why-rosmac.md` | 초안 | 6.4 대안 비교표 + 각주(REP-2000, ros2/rviz#929, RoboStack ros-noetic#459, Docker no --network=host) + 실측 수치 + "한계" 절 + Kilted 호라이즌 |

README.md 갱신: Architecture 절에 why-rosmac·troubleshooting 링크, Contributing 절 신설.

### 계획 문서와 다르게 수행한 것 + 사유
- 6.3-1 서드파티 고지 검토: SECURITY.md 위협 모델에 "바이너리는 재다운로드·sha 검증,
  재배포 아님"을 명시했으나, **정식 THIRD-PARTY-NOTICES 검토 결과 기록은 미완** (별도 항목).
- 6.1 troubleshooting.md를 6.3보다 먼저 만듦 (config.yml에서 링크가 필요해서).
- README.ko.md는 미갱신 — D11상 폐지 예정이라 신규 링크 반영 보류 (6.1에서 처리).

### 남은 P6.3 항목
- [x] CoC 연락처 확정 → `pythontogoplease@gmail.com` (사용자 결정 2026-08-31)
- [x] GitHub repo 설정 체크리스트 문서 → `docs/plan/repo-settings-checklist.md`
      (공개 전 A1~A6 / 공개 시 B / 공개 후 C 확인). Actions 권한·`pypi` env·
      branch protection·Private vulnerability reporting·Trusted Publisher 등록 포함
- [ ] 이슈 템플릿 2종 fork 실측 (렌더링 확인) — repo public 후 확인 (체크리스트 C)

## P6.3-1 서드파티 고지 검토 — PARTIAL (2026-08-31)

`THIRD-PARTY-NOTICES.md` 신설. 검토 결과:

- **바이너리는 재배포 아님** (예상대로): zenoh-bridge는 `rosmac init`이 버전+sha256
  핀으로 다운로드·검증, RoboStack/Lima/micromamba/Foxglove는 사용자 설치. 리포에
  코드 없음.
- **⚠️ 발견: 리포가 상류 예제 코드의 파생물을 재배포 중** — 고지 의무 있음:
  | 파일 | 상류 | 라이선스 |
  |---|---|---|
  | `presets/gazebo-diffbot/diffbot.launch.py` | gazebosim/ros_gz `diff_drive.launch.py` | Apache-2.0 |
  | `presets/gazebo-diffbot/diffbot_camera.sdf` | gazebosim/gz-sim `diff_drive.sdf` | Apache-2.0 |
  | `presets/nav2-diffbot/nav2_world.sdf` | gazebosim/gz-sim `diff_drive.sdf` | Apache-2.0 |
  | `presets/nav2-diffbot/nav2-diffbot.launch.py` | ros_gz/slam_toolbox/nav2 launch API 조합 | Apache-2.0 |
  | `presets/panda-moveit/demo_headless.launch.py` | moveit_resources `demo.launch.py` | BSD-3-Clause |
  | `examples/pick_demo/pick_demo.py` | (원작) panda.srdf group_state 수치만 인용 | BSD-3-Clause |
- **조치 완료**: 위 6개 파일에 SPDX + "adapted from ... , 변경점" attribution 헤더 추가.
- **라이선스 의무 완료 (2026-08-31)**:
  - [x] `LICENSES/Apache-2.0.txt`(apache.org 원문 11358B)·`LICENSES/BSD-3-Clause.txt`
        (SPDX 원문 1460B) 벤더링
  - [x] 상류 참조를 `humble` / `ign-gazebo6`(Fortress) 브랜치 + Phase 0–2 실측
        패키지 버전(ros-gz ign 6.18.0, moveit 2.5.x)으로 핀. 적응 시점에 커밋 SHA를
        기록 안 해서 정확한 SHA는 불가 — 브랜치+버전이 레퍼런스
  - [x] `pyproject.toml` `license-files = ["LICENSE", "LICENSES/*.txt",
        "THIRD-PARTY-NOTICES.md"]` → sdist·wheel 모두 `dist-info/licenses/`에 포함.
        `python -m build` + `twine check` + wheel 설치 스모크 통과, METADATA에
        `License-File:` 4항목 확인

## P6.3-5 repo 설정 적용 — 완료 (2026-08-31)

`gh api` 실측: repo public / Ruleset `main-protection` active (bypass=메인테이너) /
`pypi` env `v*` branch+tag / Actions read-only / secret scanning+push protection /
private vuln reporting / Discussions on / description+topics. 상세는
`docs/plan/repo-settings-checklist.md` 진행 상태 절.
미완: TestPyPI trusted publisher, delete-branch-on-merge(사소).
건너뜀: Phase 5.6 게이트·TestPyPI 리허설 (공개 선행, 사용자 결정).

## P6.5-1 git 이력 민감정보 스캔 — 완료 (2026-08-31), 결정 반영됨

전체 74커밋 + 전 blob 스캔:

| 항목 | 결과 |
|---|---|
| 토큰/API키/비밀번호/.pem/.env | **없음** (패턴 스캔 clean) |
| 커밋터/작성자 이메일 | `pythontogoplease@gmail.com` 단일 (사용자 본인, 공개 OK). 작성자명 `PythonToGo` + `Taey`(1커밋) 혼용 |
| 절대경로 | `tests/unit/test_psview.py`의 `/Users/u/...`(익명 `u`), `weekly.yml`의 `/Users/runner/...`(GH 러너 표준) — 문제 없음 |
| 대용량 blob | 최대 503KB (evidence PNG 스크린샷). 정상 |
| PNG 메타데이터 | `kMDItemWhereFroms` null, GPS/EXIF 노출 없음 (exiftool 미설치 — 육안 확인 권장) |

**발견 1 — Co-Authored-By 트레일러 (8커밋, E.17/E.20 범위)**: `Co-Authored-By:`
+ `Claude-Session:` 트레일러가 8개 커밋 메시지에 존재.
→ **사용자 결정 (2026-08-31): 그대로 둔다.** 세션 ID URL은 계정 소유자만 접근
  가능하고 하드 시크릿이 아님. 이력 재작성 대상에서 제외.

**발견 2 — 개인/소속 정보**: `PLAN.md` D6 등 3개 문서에 사용자의 사적 소속을
암시하는 문구가 있었음.
→ **사용자 결정 (2026-08-31): 완전 제거.** ① HEAD 순화 (PLAN.md D6, AGENTS.md
  2줄 — "무관한 별도 리포"로 교체) ② `git filter-repo --replace-text`로 전 이력
  blob에서 동일 치환 (커밋 메시지·트레일러 불변). 커밋 SHA는 4df7294 이후 전부
  변경됨 → 사용자가 `git push --force` 필요 (규칙 9, 에이전트 미실행).

**결론**: 하드 시크릿 0. 발견 2는 이력 재작성으로 제거, 발견 1은 유지 결정.

## 다음 작업 인계 메모
- 초안은 전부 `main`에 커밋됨. 문구 리뷰 후 확정.
- Phase 6.5 최종 점검(민감정보 스캔, 링크 유효성)은 5.6 게이트 통과 후.
- 6.2 데모 자산(GIF), 6.1 나머지(README 재구성·workflow 잔여), 6.4 확정은 미착수.

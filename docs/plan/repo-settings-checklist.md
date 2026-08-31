# GitHub repo 설정 체크리스트 (Phase 6.3-5 / 6.5)

> rosmac를 공개로 전환하기 전/시/후에 GitHub 웹 UI에서 해야 하는 설정.
> 코드/파일로 할 수 없는 것만 모았다. 에이전트 실행 불가 — 전부 사용자 직접.
> 순서: **A. 공개 전 (private 상태에서 미리)** → **B. 공개 전환** → **C. 공개 직후 확인**.

---

## A. 공개 전 — private 상태에서 미리 해둘 것

### A1. Actions 설정 (Settings → Actions → General)
- [ ] **Actions permissions**: "Allow all actions and reusable workflows"
      (또는 "selected" 시 `actions/*`, `pypa/gh-action-pypi-publish` 허용)
- [ ] **Workflow permissions**: "Read repository contents and packages permissions"
      (= 기본 read-only). 워크플로가 필요한 쓰기 권한은 각 파일의 `permissions:`
      블록에 이미 선언돼 있음 (`weekly.yml` = `issues: write`,
      `release.yml` = `id-token: write`)
- [ ] "Allow GitHub Actions to create and approve pull requests" — **끔** (불필요)

### A2. `pypi` Environment (Settings → Environments)
- [ ] `pypi` 이름으로 Environment 생성 (`release.yml`의 publish job이 참조)
- [ ] Deployment branches and tags: "Selected" → `v*` 태그만 허용 (권장)
- [ ] (선택) Required reviewers: 본인 추가 — publish 전 수동 승인 게이트
- [ ] Secrets/vars 추가 **안 함** — Trusted Publishing이라 토큰 불필요

### A3. Branch protection — `main` (Settings → Branches → Add rule, 또는 Rulesets)
- [ ] Require a pull request before merging
      - 단독 메인테이너라 "Require approvals"는 0 또는 1(본인 승인 불가 주의) —
        0으로 두고 아래 status check로 게이트
- [ ] Require status checks to pass before merging:
      - `ci.yml`의 job 이름은 **`checks`** → 매트릭스 3개
        (`checks (ubuntu-latest, 3.11)`, `(ubuntu-latest, 3.12)`, `(macos-14, 3.12)`)
      - [ ] "Require branches to be up to date before merging"
- [ ] Require conversation resolution before merging
- [ ] (선택) Require linear history
- [ ] Do not allow bypassing the above settings — **끔** (본인이 hotfix 가능하게)
- [ ] Rules applied to: Include administrators — 취향. 끄면 긴급 시 직접 push 가능

### A4. Security (Settings → Security / Code security)
- [ ] **Private vulnerability reporting** — 켬 (`SECURITY.md`·이슈 config가 이 경로를 안내)
- [ ] Dependabot alerts — 켬
- [ ] Dependabot security updates — 켬 (dep 표면 작아 부담 없음)
- [ ] Secret scanning + Push protection — 켬 (public 리포는 무료)
- [ ] Code scanning (CodeQL) — v0.1은 **생략** (규모 대비 가치 낮음, v0.2 재검토)

### A5. PyPI / TestPyPI Trusted Publisher (pypi.org / test.pypi.org 웹)
- [ ] **TestPyPI** (test.pypi.org → Your projects → Publishing, 또는 "pending publisher"):
      - PyPI Project Name: `rosmac`
      - Owner: `PythonToGo` / Repository: `rosmac`
      - Workflow name: `release.yml`
      - Environment name: `pypi`
- [ ] **PyPI** (pypi.org) — 동일 값으로 pending publisher 등록
- [ ] `rosmac` 이름이 아직 비어 있는지 재확인 (2026-07 기준 404 = 미점유)

### A6. General (Settings → General)
- [ ] Features: Wikis **끔**, Discussions **켬**, Issues **켬**, Projects 취향
- [ ] Pull Requests: "Allow squash merging"만 켬 (merge commit/rebase 끔 — 이력 깔끔)
      - [ ] "Automatically delete head branches" 켬
- [ ] Pages — **끔** (v0.1은 GitHub 마크다운으로 충분)

---

## B. 공개 전환 (Phase 5.6 게이트 통과 후)

- [ ] 최종 점검: CI green / README 링크·이미지 유효 / `git push`로 origin 최신화
      (main이 로컬보다 뒤처져 있지 않은지)
- [ ] Settings → General → Danger Zone → **Change visibility → Public**
- [ ] About (리포 우상단 톱니):
      - Description: `One-command ROS 2 Humble dev environment for Apple Silicon Macs`
      - Website: 비움 (또는 추후 데모 영상)
      - Topics: `ros2` `macos` `apple-silicon` `robotics` `robostack` `zenoh`
        `lima` `moveit` `nav2` `ros`
      - "Releases", "Packages" 체크 취향
- [ ] `v0.1.0` 태그 push → **Releases → Draft a new release**:
      - Tag: `v0.1.0` (main의 최신 커밋)
      - Title: `v0.1.0`
      - 본문: `CHANGELOG.md`의 `[0.1.0]` 절 복사 + 버전 핀
        (BRIDGE_VERSION, PINNED_CHANNEL, lima 하한) 명시
      - **Publish** → `release.yml`이 build→smoke→publish 자동 실행
- [ ] Actions 탭에서 `release` 워크플로 성공 확인 → pypi.org/project/rosmac 확인

---

## C. 공개 직후 확인

- [ ] **New issue** 화면에 Bug report / Feature request 템플릿 2종 + 하단
      contact link 3개(Discussions / troubleshooting / security advisory) 표시
- [ ] `docs/troubleshooting.md`·`PLAN.md` 등 이슈 템플릿 내 링크가 실제로 열림
- [ ] `pipx install rosmac` (또는 `pip install rosmac`)가 PyPI에서 됨
- [ ] `rosmac --version` → `0.1.0`, 설치본에 `LICENSES/` 포함
      (`python -c "import importlib.metadata as m; print(m.distribution('rosmac').files)"`)
- [ ] SECURITY advisory 링크(`/security/advisories/new`)가 로그인 상태에서 열림
- [ ] Discussions 탭 활성, 첫 카테고리(Q&A, Ideas, Show and tell) 존재
- [ ] (README에 CI 배지 추가했다면) 배지가 green 표시

---

## 안 하는 것 (명시)
- 조직(Org) 이전 — 개인 계정 유지
- Sponsor 버튼 — v0.1 범위 아님
- 브랜치 `feat/nav2-preset` 유지 불필요 → `git push origin --delete feat/nav2-preset`
  (이미 병합됨)
- 텔레메트리/Analytics 연동 — 하지 않음 (신뢰 자산, PLAN 비목표)

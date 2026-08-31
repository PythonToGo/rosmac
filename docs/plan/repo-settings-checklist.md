# GitHub repo 설정 체크리스트 (Phase 6.3-5 / 6.5)

> rosmac를 공개로 전환하기 전/시/후에 GitHub 웹 UI에서 해야 하는 설정.
> 순서: **A. 공개 전** → **B. 공개 전환** → **C. 공개 직후 확인**.

## 진행 상태 (2026-08-31)

- **repo 공개 완료.** `gh api`로 실측 검증:
  - A1 Actions: allow all / workflow 권한 read-only / PR 자동승인 off ✅
  - A2 `pypi` env: 존재, deployment policy `v*` **branch + tag 둘 다** ✅ (tag 규칙
    누락은 릴리스 blocker였는데 추가됨)
  - A3 Ruleset `main-protection` (active): restrict deletions / block force-push /
    require PR(0 approval)+conversation resolution / required status checks 3개
    (`checks (ubuntu-latest, 3.11)`·`(ubuntu-latest, 3.12)`·`(macos-14, 3.12)`)
    +strict / bypass = 메인테이너 계정 "always" ✅
  - A4: private vulnerability reporting ✅, Dependabot alerts+security updates ✅,
    secret scanning + push protection ✅ (공개 후 활성화)
  - A5: **PyPI** pending trusted publisher 등록 완료 (rosmac / release.yml / env pypi).
    **TestPyPI는 미등록** — 리허설 하려면 필요
  - A6: Discussions ✅ / Wiki off ✅ / squash-only ✅ / description+topics 설정 ✅
- **미완**: `delete_branch_on_merge`는 off (사소). TestPyPI trusted publisher.
- **건너뜀**: Phase 5.6 프레시 머신 게이트, TestPyPI 리허설 — 공개를 먼저 함
  (사용자 결정). v0.1.0 태깅 전에 최소 리허설 권장.

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
- [x] `pypi` 이름으로 Environment 생성 (`release.yml`의 publish job이 참조)
- [x] Deployment branches and tags → "Selected": `v*` 를 **branch 와 tag 둘 다** 추가
      ⚠️ **tag 규칙이 핵심** — `release.yml`은 `refs/tags/vX.Y.Z`에서 도는데
      tag 패턴이 없으면 publish job이 environment 정책에 막힌다
- [ ] (선택) Required reviewers: 본인 추가 — publish 전 수동 승인 게이트
- [x] Secrets/vars 추가 **안 함** — Trusted Publishing이라 토큰 불필요

### A3. Ruleset — `main` (Settings → Rules → Rulesets → New branch ruleset)
새 Rulesets UI 기준. 클래식 "Branch protection"이면 항목명이 다르지만 대응됨.

- [x] Name 임의, **Enforcement status: Active**, Target: `main` (Include by pattern
      또는 Include default branch)
- [x] **Bypass list**: 메인테이너 계정 추가, mode "Always" — 직접 push 유지
      (Ruleset은 사고 방지 + 외부 기여자 게이트로 작동)
- [x] Restrict deletions ☑ / Block force pushes ☑
- [x] Require a pull request before merging ☑ — Required approvals **0**
      (셀프 머지 즉시 가능), Require conversation resolution ☑
- [x] Require status checks to pass ☑ + Require branches to be up to date ☑
      → **+ Add checks** 로 3개 등록 (source: GitHub Actions):
      `checks (ubuntu-latest, 3.11)` · `checks (ubuntu-latest, 3.12)` · `checks (macos-14, 3.12)`
      ⚠️ `ci.yml` 매트릭스를 바꾸면 이 이름도 바뀜 → Ruleset도 갱신할 것
- [ ] Require linear history — 끔 (이력에 merge 커밋 있음)
- [ ] Require signed commits — 끔

### A4. Security (Settings → Code security)
- [x] **Private vulnerability reporting** — 켬 (`SECURITY.md`·이슈 config가 이 경로를 안내)
- [x] Dependabot alerts — 켬
- [x] Dependabot security updates — 켬
- [x] Secret scanning + Push protection — 켬 (public 리포는 무료)
- [ ] Code scanning (CodeQL) — v0.1은 **생략** (규모 대비 가치 낮음, v0.2 재검토)

### A5. Trusted Publisher
- [x] **PyPI** (pypi.org → account → Publishing): pending publisher —
      project `rosmac` / GitHub / `PythonToGo/rosmac` / `release.yml` / env `pypi`
- [ ] **TestPyPI** (test.pypi.org, 별도 계정) — 동일 값. 리허설 하려면 필요

### A6. General (Settings → General)
- [x] Features: Wikis **끔**, Discussions **켬**, Issues **켬**
- [x] Pull Requests: squash-only
      - [ ] "Automatically delete head branches" 켜기 (아직 off)
- [x] Pages — 끔
- [x] Description + Topics (`ros2 ros macos apple-silicon robotics robostack zenoh lima moveit nav2`)

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

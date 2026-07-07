# Phase 6 — 오픈소스 런칭 (문서·커뮤니티·공개)

> 목표: rosmac을 공개 저장소로 전환하고, 외부인이 신뢰하고 채택할 수 있는
> 문서·커뮤니티 기반을 갖춘 뒤 v0.1.0을 런칭한다.
> 착수 조건: Phase 5 완료 (5.6 게이트 통과 — 재현성이 증명 안 된 도구를 공개하지 않는다)
> E2E 성공 기준: 프로젝트를 모르는 제3자가 README만 보고 (a) 이 도구가 왜 필요한지
> 30초 안에 이해하고 (b) 설치에 성공한다.
> 예상 소요: 1~2주 (파트타임)
> **주의**: repo public 전환, 외부 포스팅 등 모든 공개 행위는 사용자가 직접 실행한다
> (AGENTS.md 절대 규칙 9). 에이전트는 초안·자산 준비까지만.

## 태스크 의존 그래프

```
6.1 영어 문서 전환 ─┐
6.2 데모 자산       ─┼→ 6.5 v0.1.0 런칭 (게이트: 사용자)
6.3 커뮤니티 인프라 ─┤
6.4 포지셔닝 문서   ─┘
```

---

## 6.1 영어 문서 전환 (D11)

### 배경
공개 대상 문서는 영어가 1급이어야 도달 범위가 생긴다. 내부 계획 문서(docs/plan/)는
한국어 유지 — 번역 비용 대비 가치 없음. 경계를 명확히 한다.

### 절차
1. `README.md` → 영어 재작성 (단순 번역이 아니라 공개용 재구성: 문제 → 데모 GIF →
   Quickstart → 아키텍처 한 장 → 지원 매트릭스 → FAQ 링크).
   한국어 병행판은 두지 않는다 (D11 확정 — 공개 문서는 전부 영어).
2. `docs/workflow.md` → 영어로 전환 (개발 루프, 함정표 포함 — 별도 .en 파일이 아니라
   원본 자체를 영어화, D11).
3. **`docs/troubleshooting.md` (영어) 신설**: known-issues.md(내부, 한국어)에서
   *사용자가 겪을* 항목만 추출·영역 (KI-6/16/17/19/22/23/25/26 + 데몬 hang).
   증상 문자열을 그대로 실어 검색 유입을 노린다 (에러 메시지가 최고의 SEO).
4. `--help` 텍스트 전수 영어화 (현재 한국어 혼재 여부 점검 후).

### 완료 기준 (AC)
- [ ] 영어 README 완성 — 링크 유효성 전수 확인 (상대 링크 포함)
- [ ] troubleshooting.md의 각 항목이 "증상(에러 원문) → 원인 1줄 → 해결 명령" 형식
- [ ] CLI 출력·help에 한국어 잔재 0 (grep으로 확인)

---

## 6.2 데모 자산

### 배경
이 도구의 가치("맥에서 ROS2가 그냥 된다")는 글보다 20초 영상이 잘 판다.

### 절차
1. 터미널 데모: [vhs](https://github.com/charmbracelet/vhs) 또는 asciinema로 스크립트화
   (재생성 가능해야 함 — `.tape` 파일을 repo에 커밋):
   - GIF A: `rosmac init → up → doctor` (성공 러시)
   - GIF B: `rosmac sim panda-moveit` → Foxglove에서 팔 플래닝 (화면 녹화 병행)
2. 스크린샷: Foxglove panda 레이아웃, doctor 출력, status 출력 → `docs/assets/`.
3. (선택) 60~90초 유튜브 데모 영상 — 링크만 README에.

### 완료 기준 (AC)
- [ ] GIF 2종이 README 상단에 임베드, 각 5MB 이하
- [ ] 데모 재생성 절차가 `docs/assets/README.md`에 기록 (버전 업 때 갱신 가능)

---

## 6.3 커뮤니티 인프라

### 절차
1. `LICENSE` 파일 확정 (MIT — README 선언과 일치시킴).
   **서드파티 고지**: zenoh-bridge 바이너리 재다운로드 방식이라 재배포 아님을 확인,
   RoboStack/Lima는 사용자 설치 — 고지 의무 검토 결과를 기록.
2. `CONTRIBUTING.md`: 개발 환경 셋업(.venv, pytest), 커밋 규약, e2e 실행법,
   known-issues 기여 형식 (이 프로젝트의 차별점 — "함정 DB"에 기여받는 구조).
3. `.github/`: ISSUE_TEMPLATE(bug → **`rosmac report` 번들 첨부 요구**, feature),
   PR 템플릿, `SECURITY.md`(사설 보고 경로).
4. `CODE_OF_CONDUCT.md` (Contributor Covenant).
5. GitHub repo 설정 체크리스트 문서화: About/topics(`ros2`, `macos`, `apple-silicon`,
   `robotics`), Discussions 활성화 여부, branch protection.

### 완료 기준 (AC)
- [ ] 신규 이슈 작성 화면에서 템플릿 2종이 동작 (fork로 실측 가능)
- [ ] LICENSE·고지 검토 결과가 phase6-results.md에 기록

---

## 6.4 포지셔닝 문서 ("왜 rosmac인가")

### 배경
공개 직후 반드시 나올 질문 — "Docker 쓰면 되잖아?" — 에 문서로 선제 대응한다.
Phase 0 리서치가 근거 자산이다.

### 절차
`docs/why-rosmac.md` (영어): 대안 비교표 + 각 대안이 막히는 실측 지점.

| 접근 | 막히는 지점 |
|---|---|
| Docker (amd64 이미지) | Rosetta 에뮬레이션 성능, GUI/GPU 없음, DDS가 컨테이너 경계에서 동일 문제 |
| Docker (arm64) + XQuartz | RViz/Gazebo GUI 불안정, 개발 루프가 컨테이너 안에 갇힘 (IDE 통합 상실) |
| RoboStack 단독 (맥 네이티브만) | Gazebo/MoveIt full 스택 불가 또는 불안정, RViz2 구조적 실패 (ros2/rviz#929) |
| UTM/Parallels full VM | 개발도 VM 안 → IDE·파일공유·성능 저하, GUI 스트리밍 병목 |
| **rosmac (레이어 분리)** | 개발은 네이티브, 무거운 것은 Tier 1 VM, 경계는 zenoh — 각 레이어가 가장 잘 되는 곳에서 |

+ 한계 정직하게: VM 메모리 상주, GPU 가속 없음(Phase 3 실험 중), Humble 한정.

### 완료 기준 (AC)
- [ ] 비교표의 모든 주장에 근거(실측 기록 또는 공개 이슈 링크) 각주
- [ ] "한계" 절 존재 — 과장 없는 포지셔닝

---

## 6.5 v0.1.0 런칭 (게이트: 사용자 실행)

### 절차
1. 최종 점검 체크리스트: CI green / README 링크·GIF / LICENSE / pyproject 메타데이터 /
   `git log` 민감정보 스캔 (초기 커밋부터 — 경로·이메일·토큰).
2. 사용자 실행 항목 (에이전트는 초안만):
   - repo **public** 전환 + `v0.1.0` tag → Release (5.5 자동화가 PyPI publish)
   - 런칭 포스트: ROS Discourse(가장 중요 — macOS 스레드 다수 존재), r/ROS,
     RoboStack 커뮤니티 채널. 각 초안을 `docs/plan/launch-drafts/`에 준비.
3. 런칭 후 1~2주 이슈 대응 창구 운영 — 들어온 문제는 known-issues 파이프라인으로.

### 완료 기준 (AC)
- [ ] 점검 체크리스트 전 항목 통과 기록
- [ ] 포스트 초안 3종 준비 (Discourse/reddit/RoboStack) — 발행은 사용자
- [ ] 런칭 후 첫 외부 이슈/질문에 24~48h 내 응답 (프로세스 확인)

## 명시적 비목표
- 문서 사이트(mkdocs 등) 구축 — v0.1은 GitHub 마크다운으로 충분, 문서량 늘면 v0.2에서
- 로고/브랜딩 디자인 (있으면 좋지만 게이트 아님)
- "ROS" 상표: 프로젝트명이 ros- 접두가 아니고(rosmac) 비상업 오픈소스 —
  Open Robotics 상표 정책 확인만 하고 기록 (R9)

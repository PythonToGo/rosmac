# Phase 6 — 출판 (페이퍼·발표)

> 목표: rosmac을 학술·커뮤니티 채널에 공식 출판물로 남긴다 — 인용 가능한 DOI,
> 그리고 (선택) 발표.
> **범위 (D13, 2026-07-07)**: 이 Phase는 **제출 준비까지만**이다. JOSS 제출·ROSCon
> 신청 등 실행은 사용자가 별도 지시할 때까지 하지 않는다 (6.4는 보류 상태).
> 착수 조건: Phase 5 완료 (공개 repo가 출판의 전제 — JOSS는 공개 저장소 요구)
> 성공 기준: 제출 가능 상태 완성 (paper.md 컴파일 통과 + JOSS 체크리스트 전 항목 충족)
> 예상 소요: 2~4주 (파트타임, venue 리뷰 대기는 별도)

## venue 전략 (D13 — 사용자 승인 필요)

| venue | 형태 | 적합성 | 비고 |
|---|---|---|---|
| **JOSS** (Journal of Open Source Software) | 소프트웨어 페이퍼 (paper.md 0.5~2p) + 코드 리뷰 | **1순위** — "연구를 가능하게 하는 도구" 카테고리에 정확히 부합, 리뷰가 곧 품질 검증, DOI 발급 | 무료, 공개 리뷰. Phase 4~5 산출물이 요구사항과 거의 1:1 |
| ROSCon 발표 (lightning/일반) | 발표 + 영상 아카이브 | 병행 — ROS 커뮤니티 도달 최적 | CFP 시즌 확인 필요, 채택 경쟁 |
| IEEE ICRA/IROS tool paper·워크숍 | 정식 논문 | 후순위 — 신규 연구 기여 주장 필요, 비용 대비 리스크 큼 | JOSS 이후 확장판으로만 검토 |

근거: rosmac의 기여는 새 알고리즘이 아니라 **엔지니어링 통합과 실측 함정 DB**다.
JOSS는 정확히 이런 기여를 위해 존재하고, 리뷰 과정 자체가 제품 품질을 올린다.

## 태스크 의존 그래프

```
6.1 평가 데이터 확정 ─→ 6.3 paper.md 작성 ─→ 6.4 제출 (사용자)
6.2 JOSS 요건 갭 분석 ─┘        ROSCon 초록은 6.3에서 파생
```

---

## 6.1 평가 데이터 확정 (재현 가능한 벤치마크)

### 배경
Phase 0/2의 실측치(브리지 10.3MB/s, RTF 0.99, 카메라 14.4fps)가 있으나
일회 측정 조건이 흩어져 있다. 출판용으로는 **하나의 재현 스크립트**로 묶는다.

### 절차
1. `tests/bench/` 신설: 브리지 스루풋/레이턴시, MoveGroup 액션 왕복 시간,
   Gazebo RTF(물리/카메라), 카메라 E2E fps, `rosmac init→up` 소요, 메모리 상주량.
   각 3회 측정 중앙값, 결과 JSON 출력 (검증 철학 준수).
2. 비교 베이스라인 1개 이상: 최소한 "VM 단독 개발"(모든 것을 VM에서) 대비
   개발 루프 시간(코드 수정→노드 재실행) 비교 — rosmac의 핵심 주장을 정량화.
3. 결과를 `docs/plan/phase6-results.md` + 페이퍼 표로 정리 (HW/버전 명기).

### 완료 기준 (AC)
- [ ] `python -m tests.bench` 한 번으로 전 지표 재측정 가능
- [ ] 페이퍼에 들어갈 표가 스크립트 출력에서 기계적으로 재생성됨

---

## 6.2 JOSS 요건 갭 분석

### 절차
JOSS 리뷰 체크리스트를 기준으로 현재 상태를 표로 대조:

| JOSS 요건 | 담당 산출물 | 상태 확인 |
|---|---|---|
| OSI 라이선스 | LICENSE (5.3) | |
| 설치 문서·의존성 명시 | README Quickstart (4.6 검증) | |
| 자동 테스트 | unit + CI (4.4) | |
| 예제/사용 문서 | workflow.en.md, 프리셋 (5.1) | |
| 기여 가이드 | CONTRIBUTING (5.3) | |
| Statement of need | paper.md (6.3) | |
| 아카이브 DOI | Zenodo 연동 → 릴리스 스냅샷 | |
| substantial scholarly effort | 커밋 이력 + 함정 DB + 벤치마크 | |

갭이 나오면 해당 Phase 태스크로 되돌려 보수한다.

### 완료 기준 (AC)
- [ ] 갭 분석표 전 행 "충족" + 근거 링크
- [ ] Zenodo-GitHub 연동 설정 문서화 (활성화는 사용자)

---

## 6.3 paper.md 작성 (+ ROSCon 초록 파생)

### 절차
1. JOSS `paper.md` (250~1000 단어) 구조:
   - **Summary**: 레이어 분리 아키텍처 한 문단 + 그림 1장 (PLAN.md 2절 다이어그램 정리)
   - **Statement of need**: REP-2000 Tier 격차, RViz2 macOS 구조적 실패(ros2/rviz#929),
     기존 접근(Docker/VM 단독)의 한계 — Phase 0 리서치와 why-rosmac.md에서 압축
   - **Functionality**: init/up/doctor/sim/shell + 함정 DB 26항 (연구자 시간 절약 주장)
   - **Evaluation**: 6.1 표
   - **Acknowledgements / References**: zenoh-bridge-ros2dds, RoboStack(논문 있음 — 인용),
     Lima, Foxglove
2. `paper.bib` 작성. 공저자/ORCID는 사용자 확인.
3. ROSCon 초록(300단어)을 paper.md에서 파생 — CFP 일정에 맞춰 별도 보관.

### 완료 기준 (AC)
- [ ] paper.md가 JOSS 컴파일 통과 (openjournals 도구 로컬/CI 검증)
- [ ] 모든 정량 주장에 6.1 데이터 또는 phase-results 근거
- [ ] 사용자 리뷰 1회 반영

---

## 6.4 제출 (보류 — 사용자 지시 시에만 활성화, D13)

### 절차
1. 최종 번들: 태그된 릴리스 + Zenodo DOI + paper.md.
2. **JOSS 제출은 사용자가 직접** (계정·저자 책임). 에이전트는 제출 폼 입력값 초안 준비.
3. 리뷰어 코멘트 대응 루프: 이슈로 들어오는 리뷰를 태스크화해 처리 (보통 4~8주).

### 완료 기준 (AC)
- [ ] 제출 완료 (제출 번호 기록)
- [ ] 리뷰 대응 프로세스 문서화 (누가/어떻게 — 사용자와 에이전트 역할 분담)

## 명시적 비목표
- 정식 학회 full paper (JOSS/ROSCon 결과를 본 뒤 별도 판단)
- 벤치마크에서 타 도구 폄하 — 비교는 사실·실측·링크로만

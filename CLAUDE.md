# rosmac

**시작 전에 `AGENTS.md`를 반드시 전체 읽을 것** — 작업 규칙, 배경지식, 용어집이 거기 있다.

요약 (상세는 AGENTS.md):
- 계획 문서: `PLAN.md`(아키텍처·결정로그·리스크) + `docs/plan/phaseN-*.md`(태스크 상세)
- 절대 금지: SIP 비활성화(`csrutil disable`), 사용자 글로벌 환경 임의 변경,
  결정 로그(D1~D14) 무단 변경, AC 검증 없는 완료 표기,
  **외부 공개 행위**(git push, repo public 전환, PyPI publish, 포럼 포스팅 등 —
  사용자 직접 또는 명시 승인 필요, AGENTS.md 규칙 9)
- 막히면: `docs/plan/known-issues.md` → 태스크의 "실패 시 대응" → 2회 실패 시 사용자 보고
- 결과는 `docs/plan/phaseN-results.md`에 기록, 커밋 메시지 `[PX.Y] 요약`
- 실험 파일은 `~/rosmac_spike/`, `~/workspace/macros`는 무관한 리포이므로 건드리지 않음

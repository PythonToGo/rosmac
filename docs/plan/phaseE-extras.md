# E 트랙 — 상품성 점검(2026-07-08) 파생 태스크

> 출처: Run F(CI) 착수 전 상품성·완비성 점검 (경쟁 조사 결론·수리 내역은
> [phase5-results.md](phase5-results.md) "부수 작업 — 상품성 점검" 절).
> **전부 비게이트** — Phase 5→6 진행을 막지 않으며, 개별 착수/생략 가능.
> 이미 완료된 수리(LICENSE, pyproject 메타데이터, README 영어 메인+한국어)는
> 여기 없음 — 커밋 `27d4a21` 참조.

## E.1 docs/workflow.md 영어 메인 + 한국어 병행

- **배경**: README를 영어 메인(README.md)+한국어(README.ko.md)로 개편했는데,
  README가 링크하는 workflow.md(개발 루프·pick_demo 예제)는 아직 한국어뿐 —
  외부 사용자 여정이 Quickstart 다음 단계에서 끊긴다.
- **작업**: workflow.md를 영어로 전환, 한국어는 workflow.ko.md로 분리, 양쪽
  README에서 각각 링크. 코드 블록·실측 값은 불변.
- **AC**: [ ] 영어 workflow.md + 한국어 workflow.ko.md 상호 링크
  [ ] 명령·출력 예시가 현행 CLI(영어 출력)와 일치

## E.2 리스크 레지스터에 R11(네이티브 macOS ROS 2 성숙) 등록 — ✅ 완료 (2026-07-08)

- **배경**: 경쟁 조사 결과 ROS 2 Kilted + Gazebo Ionic + ros2_control의 macOS
  네이티브 데모가 진행 중(2025-12~, "serious preview"). 성숙 시 "VM이 필요한
  이유"의 절반이 침식된다.
- **작업**: PLAN.md 리스크 레지스터에 R11 등록 (본 커밋에서 수행). 완화 방향:
  위협이 아니라 흡수 — E.5의 "네이티브/VM 자동 판단 레이어"가 대응책.
- **AC**: [x] PLAN.md 5절에 R11 행 존재

## E.3 PyPI 이름 선점 (P5.5 선행, **사용자 액션**)

- **배경**: `rosmac`이 PyPI에 미점유(404 실측 2026-07-08). P5.5(패키징·배포)의
  전제인데 이름은 선착순.
- **작업**: 사용자가 직접 PyPI 계정으로 0.1.0(또는 dev 프리릴리스) 업로드 —
  절대 규칙 9(외부 공개 행위)라 에이전트 실행 불가. 에이전트는 `hatch build`
  산출물 검증까지 지원.
- **AC**: [ ] pypi.org/project/rosmac 존재 + 소유 계정 확인

## E.4 GitHub 리포 메타 정비 (공개 시점, P6.5와 묶음)

- **배경**: 조사에서 뽑은 셀링포인트를 발견 경로(GitHub 검색·About·topics)에도
  반영해야 함.
- **작업**: repo description(영어 헤드라인 1문장), topics(ros2, macos,
  apple-silicon, robostack, zenoh, lima, robotics), About 링크. 공개 전환과
  동시에(규칙 9 — 사용자 실행).
- **AC**: [ ] description/topics 설정 스크린샷 또는 gh api 확인

## E.5 로드맵 후보 백로그 (결정 대기 — D 결정 필요)

경쟁 조사에서 확인된 랜드스케이프 공백 3개. 착수 여부는 Phase 6 이후 사용자 결정:

1. **네이티브/VM 자동 판단 레이어** — "네이티브에 있는 것은 네이티브로, 없는
   것만 VM으로"를 배포판·패키지 단위로 자동 판단 (deps/push의 확장).
   R11(네이티브 성숙)을 위협에서 흡수로 바꾸는 구조적 대응.
2. **doctor의 탈-맥 확장** — DDS 디스커버리 진단·복구(doctor/--fix/report)를
   리눅스에서도 쓸 수 있는 "ROS 환경 신뢰성 도구"로. KI-28류 실측 데이터가
   콘텐츠 자산.
3. **교육/팀 온보딩 모드** — "강의실 M-시리즈 30대를 15분 안에 동일 환경으로"
   + `rosmac report`로 조교 원격 트리아지. The Construct(€40/월)·Codespaces가
   못 하는 로컬 하드웨어 시나리오.

## E.6 LICENSE 저작권자 표기 확인 (**사용자 확인 1분**)

- **배경**: LICENSE 신설 시 "Copyright (c) 2026 Taeyoung Kim"으로 기재 —
  표기(실명/핸들/병기)는 사용자 결정 사안.
- **AC**: [ ] 사용자 확인 (수정 필요 시 LICENSE + pyproject authors 동기화)

# Phase 4.5 — 완성도 보강 (비게이트)

> 성격: **있으면 좋음, 게이트 아님.** Phase 5(제품화) 착수를 막지 않는다 —
> 병행하거나, 일부만 하거나, 전부 생략해도 Phase 5~7 진행에 지장 없다.
> 단, 착수한 태스크는 AC까지 완주한다 (반쯤 된 기능을 남기지 않는다).
> 착수 조건: 없음 (Phase 2 이후 아무 때나)
> 예상 소요: 태스크당 1~3일

## ⚠️ 실행 에이전트 지침
`AGENTS.md` 전체를 먼저 읽는다. 커밋 `[P4.5.X] 요약`, 결과는
`docs/plan/phase4.5-results.md`. ros2 CLI는 반드시 `rosmac shell` 경유
(env 5종 주입 — phase4-features.md 상단 지침과 동일).

---

## 4.5.1 사용자 정의 프리셋 (`~/.rosmac/presets/`)

### 배경
내장 프리셋은 2개(panda-moveit, gazebo-diffbot)뿐이고, 사용자가 자기 launch를
`rosmac sim`으로 등록할 방법이 없다.

### 설계
- `sim.py`의 프리셋 로더가 내장 assets에 더해 `~/.rosmac/presets/<name>.yaml`
  (+ 동명 디렉토리의 자산)을 읽게 확장. **이름 충돌 시 사용자 것이 우선**하되
  경고 1줄 출력.
- `rosmac sim list`에 출처 컬럼(내장/사용자) 추가.
- 스키마 검증: 기존 Preset pydantic 모델로 로드하다 실패하면 "어느 필드가 왜"를
  출력 (스택트레이스 금지).
- 문서: workflow.md에 "프리셋 만들기" 절 — 내장 panda-moveit.yaml을 주석 달린
  템플릿 예시로 사용.

### 완료 기준 (AC)
- [ ] 사용자 프리셋(내장 복사·이름 변경)으로 `rosmac sim <이름>` READY 도달 실측
- [ ] 깨진 YAML/필수 필드 누락 시 친화적 에러 (실제 출력 첨부)
- [ ] 이름 충돌 우선순위 + 경고 실측

---

## 4.5.2 `rosmac env` — eval용 환경 출력

### 배경
IDE·CI·스크립트는 서브셸(`rosmac shell`)이 아니라 **환경변수 그 자체**가 필요하다.
현재 사용자는 rosmac이 주입하는 env 5종을 손으로 재구성해야 한다 (KI-6 위험).

### 설계
`rosmac env [--shell zsh|bash|fish]` → stdout에 export 문만 출력 (rich 장식 금지 —
`eval "$(rosmac env)"`가 목적. 진단 메시지는 stderr로):
```sh
export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DISTRO=humble
export CYCLONEDDS_URI=file:///Users/<u>/.rosmac/cyclonedds.xml
export COLCON_DEFAULTS_FILE=/Users/<u>/.rosmac/colcon-defaults.yaml   # P4.1 이후
```
conda env 활성화까지는 하지 않는다 (micromamba hook은 셸마다 달라 깨지기 쉬움) —
"micromamba activate ros_env 후 eval"을 안내 주석으로 첫 줄에 출력.

### 완료 기준 (AC)
- [ ] `eval "$(rosmac env)"` 후 `ros2 topic list`가 rosmac shell과 동일 결과 (실측)
- [ ] 출력이 순수 POSIX export 문만 포함 (파이프 안전 — `rosmac env | sh -n` 통과)
- [ ] workflow.md의 IDE 통합 절 갱신 (VS Code settings 예시 포함)

---

## 4.5.3 RViz2 지위 재평가 — 문서·doctor 반영

### 배경 (실측 근거)
D4는 RViz2를 "보조"로 규정했지만, 2026-07-07 실사용에서 RoboStack RViz2가
마커·URDF·TF 시각화를 네이티브로 정상 수행했다. **D4를 바꾸지 않는다**
(Foxglove 1급 유지 — 결정 변경은 사용자 승인 사안). 다만 "동작한다"는 실측을
사용자 가치로 전환한다.

### 절차
1. doctor에 정보성 체크 추가 (FAIL 아님, INFO 등급): `rviz2` 바이너리 존재 +
   `rviz2 --help` exit 0 (GUI 기동 테스트는 하지 않는다 — CI 불가).
2. workflow.md에 "RViz2 네이티브 사용" 절: 되는 것(마커/URDF/TF/RobotModel,
   실측 2026-07-07), 알려진 한계(ros2/rviz#929 계열 불안정 가능성, 크래시 시
   Foxglove 폴백), `rosmac shell`에서 실행해야 하는 이유(KI-6).
3. known-issues에 "RViz2가 뜨는데 로봇이 안 보임" 항목 추가 — 오늘의 진단 트리
   (RobotModel Status → TF → /joint_states 발행자 → `rosmac ps`) 요약.

### 완료 기준 (AC)
- [ ] doctor INFO 체크 동작 (rviz2 있는/없는 env 양쪽 mock 테스트)
- [ ] 문서 2건 갱신 — 진단 트리는 오늘 세션의 실제 순서와 일치해야 함

---

## 4.5.4 Foxglove 레이아웃 자동화 재조사 (timebox: 1일)

### 배경
P2.5에서 딥링크로 레이아웃 임포트가 불가해 "Import 안내"로 후퇴했다.
Foxglove 앱은 자주 갱신되므로 1일 timebox로 재조사만 한다.

### 절차
1. 현행 Foxglove 데스크톱 버전에서 확인: ① `foxglove://` 딥링크 파라미터에
   layout 지정이 생겼는지 ② 로컬 레이아웃 저장 위치
   (`~/Library/Application Support/Foxglove Studio/` 계열)에 JSON을 직접 놓으면
   인식하는지 (앱 재시작 포함 실측).
2. ②가 되면: `rosmac viz --layout`이 파일 설치까지 하도록 확장 —
   단 **앱 데이터 디렉토리 쓰기는 사용자 동의 프롬프트** 후에만 (절대 규칙 2의 정신).
3. 둘 다 안 되면: 현행 안내 유지, 조사 결과와 재평가 시점(6개월)을 results에 기록.

### 완료 기준 (AC)
- [ ] 조사 결과 기록 (버전 명시) + 가능/불가 판정
- [ ] (가능 시) `rosmac viz --layout panda`가 Import 수동 단계 없이 레이아웃 적용 실측

## 명시적 비목표
- Foxglove 확장(extension) 개발, 커스텀 패널
- 프리셋 마켓플레이스류 공유 기능

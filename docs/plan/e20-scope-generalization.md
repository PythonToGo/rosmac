# E.20 대형 스택 1급화 — 브리지 스코프 일반화 (S0~S5)

> 등록: 2026-07-11 (E.17 N2/N3 파생, 사용자 지시).
> 상위 항목: [phaseE-extras.md](phaseE-extras.md) E.20.

## ✅ S0 결과 — 전제 붕괴, 태스크 대부분 폐기 (2026-07-12)

**S0 게이트 실측이 이 태스크의 전제("대형 스택은 스코핑이 전제")를 반증했다.**

- **포화 상한 스윕**: 스코프 레벨 L0(액션1·서비스0)~L3(액션12·서비스155) 및 완전
  무스코프 전부 맥에서 `navigate_to_pose` **AVAILABLE**. 포화 상한 없음.
- **진짜 원인**: 스택 재기동 시 브리지가 죽은 스택 라우트를 누적(KI-17 계열) →
  새 스택 액션 디스커버리 오염. **동일 스택** 브리지 재시작 전 0/6 → 후 4/4,
  goal 3/3. 엔티티 포화 아님. (KI-30 재작성.)
- **진짜 해법**: `rosmac sim`이 시작 시 브리지 세션 리셋(sim.py
  `_reset_bridge_session`) — E.17에서 구현·검증(fresh 3/3, churn 후 성공).
  스코핑 메커니즘·bridge_allow 제거.
- **launch 신뢰성**: 별도 실측 버그(TimerAction 촘촘 → nav2 lifecycle 간헐
  미활성)를 stagger 타이밍으로 수정(연속 7회 건강). E.17에 반영.

**결론: S1~S5(스코프 번들·오버레이·BYO 등)는 불필요 — 스코핑 자체가 필요 없다.**
Nav2는 이미 기본 브리지로 MoveIt과 동등하게 동작한다. 유일하게 남는 1급화 갭은
**맥측 msg 자동 설치(구 S3)** 하나이며, 아래 잔여 항목으로 축소한다.

### 잔여 (E.20에서 살아남은 유일 항목) — ✅ 완료 (2026-07-12)
- **맥측 msg 의존 자동 설치**: 프리셋 `mac_env_pkgs` 필드 + `rosmac sim`이 맥
  conda env에 nav2_msgs 등 보장(멱등). goal "server not available" 침묵 실패 제거.
  MoveIt(moveit_msgs)도 동일 필드로 커버 가능.
- **구현**: `deps.ensure_installed(cfg, pkgs)`(기존 installed_packages/install_missing
  재사용), cli sim에서 호출. nav2-diffbot.yaml `mac_env_pkgs=[ros-humble-nav2-msgs]`.
  유닛 2개(설치·멱등). **E2E**: nav2-msgs 제거 → `rosmac sim nav2-diffbot`이
  자동 설치("✓ Mac env packages installed") → READY. 96 tests, ruff/mypy clean.
- **이로써 E.20 종료** — 1급화 갭 전부 해소(스코핑은 애초에 불필요, S0 참조).

---

> 아래는 등록 당시(2026-07-11) 원 계획 — **S0에서 전제가 반증되어 S1~S5는 폐기**.
> 사료로 보존.
>
> 선행: [E.17](e17-nav2.md), 근거(당시): KI-30(무스코프 브리지 포화 — 오진).

## 왜 하는가 — 현재의 비대칭 (E.17 N2/N3 판단)

MoveIt이 rosmac에서 **1급**인 이유는 프리셋이 있어서가 아니라, **기본(무스코프)
브리지가 MoveIt 통신을 그대로 감당**하기 때문이다. move_group 서비스는 ~30–40개로
포화 임계 아래라, 사용자가 **자기 MoveIt 워크스페이스**를 `deps`→`shell`→
`colcon build`로 올리면 그냥 동작한다. 데모(panda-moveit)뿐 아니라 임의의 MoveIt
앱이 된다.

Nav2는 서비스 174개가 임계를 넘어(KI-30) 무스코프로는 안 되고, **프리셋이 손으로
큐레이션한 화이트리스트**로만 된다. 그 목록은 실제로 **액션 12개 중
`/navigate_to_pose` 1개 + 서비스 0개 + 시각화 토픽 한 줌**만 노출한다
(nav2-diffbot.yaml bridge_allow). 즉 "Nav2 능력"이 아니라 "이 데모의 단일 goal
경로"만 열린 상태다. 따라서:

- 사용자 **자기 Nav2**(다른 로봇·waypoint following·커스텀 costmap)는 프리셋을
  포크해 bridge_allow를 손으로 늘려야 한다 — MoveIt의 "가져와서 빌드하면 됨"이 아님.
- 워크스페이스가 필요로 하는 인터페이스를 유도하는 `deps` 같은 장치가 없다.
- 맥에서 goal을 보내려면 `nav2_msgs`를 수동 설치해야 한다(자동화 없음).

**이 비대칭은 광택이 아니라 스케일에 뿌리를 둔다.** E.17 A안(프리셋별 화이트리스트)은
데모 하나를 동작시키는 실용해였지, Nav2를 일반적 1급 능력으로 만드는 해법은 아니다.
E.20의 목표는 스코핑을 **프리셋 고정 목록 → 재사용·확장 가능한 인터페이스 번들
모델**로 일반화해, 임의의 대형 스택(사용자 Nav2 포함)이 손목록 편집 없이 동작하게
하는 것이다.

## 1급의 판정 기준 (S4에서 실증할 것)

MoveIt과 **동등**하다고 말할 수 있으려면:
1. 사용자가 **자기 대형 스택**(다른 로봇·설정의 Nav2)을 프리셋 포크 없이 맥에서
   구동할 수 있다.
2. 단일 goal을 넘어 **의미 있는 인터페이스 표면**(waypoint·다중 goal 등)이 맥에서
   쓰인다.
3. goal 전송이 조용히 실패하지 않는다(맥측 msg 의존 자동 충족).
4. 위가 브리지 포화를 재유발하지 않는다(측정된 상한 내).

## 미리 아는 리스크 / 제약

| # | 리스크 | 대응 |
|---|---|---|
| 1 | 인터페이스를 더 열수록 다시 포화(KI-30 재발) — "얼마나 열 수 있나"가 미지수 | S0 스파이크에서 **노출 상한을 정량 측정**. 상한이 낮으면 "핵심 goal 경로만"으로 설계 확정 |
| 2 | 스코프 모델이 기존 검증된 소형 프리셋(panda/diffbot 무스코프)에 회귀 | 무스코프(bridge_allow None)는 기본 유지 — 번들은 opt-in. 회귀 테스트 |
| 3 | 사용자 오버레이가 서비스류를 무분별 허용 → 포화 | 오버레이도 카테고리 명시, service_servers 기본 deny 유지. lint/경고 |
| 4 | 브리지 포화 자체를 푸는 근본책(cyclonedds/zenoh 튜닝, 다중 참가자)이 더 단순할 수도 | S0에서 **먼저 스파이크** — 상한을 올릴 수 있으면 스코핑 일반화 부담이 줄어듦 |
| 5 | 자동 스코프 유도(실행 스택 introspection)가 액션 하위 엔티티(feedback/status/tf/clock)를 놓침 | S4에서 유도 규칙을 액션→하위엔티티+tf/clock까지 전개, 실측 대조 |

## 단계별 계획

### S0 — 스코프 모델 설계 + 포화 상한 스파이크 (~1.5시간, 설계+측정, **게이트**)

- **작업**:
  - (측정) 포화 상한 스파이크: nav2 스택을 띄운 채 bridge_allow를 점진 확장
    (액션 1→12, 서비스 0→N)하며 맥 디스커버리가 깨지는 지점을 **정량화**.
    부수로 cyclonedds `MaxAutoParticipantIndex`·소켓 버퍼·zenoh config로 상한을
    올릴 수 있는지 1차 확인(리스크 4).
  - (설계) 일반 스코프 모델 결정 — 3요소:
    ① **재사용 번들**: 이름 붙은 allow-set(예: `nav2-core`, `nav2-waypoints`,
       `moveit`)을 자산으로 두고 프리셋이 참조.
    ② **오버레이 병합**: 최종 스코프 = 번들 ∪ 프리셋 extras ∪ 사용자 오버레이
       (config/워크스페이스). 병합·우선순위 규칙 확정.
    ③ **공개 인터페이스 원칙**: 무엇이 경계를 넘는가 — goal-facing 액션 +
       그 하위 토픽(feedback/status) + tf/clock + 시각화 토픽; 노드 간 내부
       서비스는 deny. 이 원칙을 문서화.
- **AC**: [ ] 노출 상한 수치 기록(액션 N개·서비스 M개까지 안전) [ ] 모델 3요소
  결정을 이 문서에 기록 [ ] **제안 D-결정 초안**(브리지 스코프 모델 — D3 인접,
  사용자 승인 대기) 작성
- **실패 시 대응**: 상한이 "단일 goal + viz"만 허용할 만큼 낮으면, 1급화 범위를
  "BYO 단일-goal Nav2"로 축소하고 사용자에게 보고(2회 실패 규칙 준용).

### S1 — 재사용 스코프 번들 + 리졸버 (~2시간, code)

- **작업**: `assets/bridge-scopes/*.yaml` 번들 + `sim.py`(또는 신규 `scope.py`)에
  리졸버 — 번들 참조를 로드해 프리셋 `bridge_allow`(인라인)와 병합. nav2-diffbot을
  인라인 목록 → `bridge_scope: nav2-core` 참조로 리팩터. doctor 토픽 주입 유지.
- **AC**: [ ] 번들 참조·병합·우선순위 유닛 [ ] nav2-diffbot이 번들 참조로 동작
  (E2E 회귀: 맥 goal 3/3 유지) [ ] 무스코프 프리셋(panda/diffbot) 무회귀
  [ ] tests green, ruff/mypy clean
- **실패 시 대응**: 병합 규칙 모호하면 S0 결정으로 회귀.

### S2 — Nav2 항법 표면 확장 (~2시간, code+E2E)

- **작업**: `nav2-core` 번들에 S0 상한 내에서 의미 있는 표면 추가 —
  `/navigate_through_poses`·`/follow_waypoints`(+ 필요한 하위 토픽). `nav2-waypoints`
  번들 분리 검토. 맥에서 **waypoint following** E2E.
- **AC**: [ ] 맥에서 follow_waypoints 또는 navigate_through_poses goal SUCCEEDED
  [ ] 확장 후에도 서비스/액션 라우팅 안정(포화 없음) 실측 [ ] 능력 매트릭스
  근거 갱신
- **실패 시 대응**: 확장이 포화 유발 시 S0 상한으로 롤백, 번들을 최소 goal로 고정.

### S3 — 맥측 msg 의존 자동 설치 (~1.5시간, code)

- **작업**: 프리셋/번들에 맥측 msg 패키지 선언(`mac_env_pkgs`: nav2_msgs 등).
  `rosmac sim`이 `ensure_apt`의 맥 대응판으로 micromamba env에 보장(멱등).
  goal이 "server not available"로 조용히 실패하는 함정 제거. MoveIt(moveit_msgs)도
  자동 수혜.
- **AC**: [ ] 맥 env에 nav2_msgs 없던 상태에서 `sim nav2-diffbot` 후 goal 즉시
  가능 실측 [ ] 이미 있으면 skip(멱등) [ ] 유닛(선언→설치 호출)
- **실패 시 대응**: RoboStack에 해당 msg가 없으면(커버리지 갭) 경고 + 수동 안내로
  degrade, E.19 커버리지 조사와 연계.

### S4 — 자기 대형 스택 가져오기 (1급 판정, ~2시간, code+E2E)

- **작업**: 사용자가 프리셋 포크 없이 자기 Nav2를 구동하는 경로 —
  (a) **선언 오버레이**: 사용자 config/워크스페이스의 `bridge_allow` 오버레이를
      번들에 병합, 또는
  (b) **실행 스택 유도**: 뜬 스택의 공개 액션을 introspection해 allow-set 자동
      생성(액션→하위엔티티+tf/clock 전개). S0 결정에 따라 택1 또는 병행.
  두 번째(다른 로봇/설정) Nav2 구성으로 실증.
- **AC**: [ ] 프리셋과 **다른** Nav2 설정이 오버레이 선언(또는 자동 유도)만으로
  맥 goal SUCCEEDED — 코드 포크 없음 [ ] 판정 기준 4항(왜 하는가) 충족 기록
- **실패 시 대응**: 자동 유도가 하위 엔티티를 놓치면 선언 오버레이로 확정, 유도는
  백로그.

### S5 — 문서/매트릭스/결정 로그 (~30분, docs)

- **작업**: 스코프 모델·번들·BYO 경로 문서화(workflow en/ko). 능력 매트릭스를
  "대형 스택 — 브리지 스코프로 1급" 표현으로 갱신. **PLAN.md 결정 로그에 D-결정
  추가**(S0 승인분). KI-30에 "일반화 완료(E.20)" 반영. CHANGELOG.
- **AC**: [ ] 영/한 정합 [ ] 결정 로그 D행 [ ] KI-30·매트릭스 갱신

## 비목표 (백로그)

- 브리지 포화의 근본 해결(zenoh/cyclonedds 재설계) — S0에서 저비용 튜닝만 확인,
  대규모 재설계는 별도.
- Nav2 플러그인/behavior tree 커스터마이징 가이드 — 프레임워크 문서 영역.
- 실로봇 위 Nav2 배포 — E.15 R5(실기) 이후.
- 배포판 전환(Jazzy/Lyrical)과의 결합 — E.5-4.

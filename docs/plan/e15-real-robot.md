# E.15 실로봇 연결 — 단계별 계획 (R0~R6)

> 등록: 2026-07-09 (E 트랙 3차 — "rosmac으로 불가능한 것" 점검 파생).
> 상위 항목: [phaseE-extras.md](phaseE-extras.md) E.15.
> **비게이트** — Phase 5/6 진행을 막지 않음. 단 R5(실기 검증)는 사용자 하드웨어
> 접근이 전제라, R0~R4는 대리 로봇으로 완결하고 R5만 하드웨어 확보 시점으로 미룬다.

## 왜 하는가

- 현재 rosmac은 맥↔VM 폐쇄 루프다. 실로봇(TurtleBot, RPi 기반 로봇 등)이 같은
  LAN에 있어도 연결 경로가 없다 → "시뮬 전용 장난감" 인상.
- 기술적으로는 **기존 아키텍처의 자연 연장**이다: 맥 브리지는 이미 zenoh 클라이언트로
  VM 브리지(tcp/127.0.0.1:7447)에 붙는다(bridge.py:97). 로봇에 zenoh-bridge-ros2dds를
  하나 더 두고 맥 브리지가 엔드포인트를 추가로 물면 끝 — DDS 멀티캐스트가 WiFi를
  건너지 않는다.
- **셀링포인트 보너스**: ROS-over-WiFi의 악명 높은 멀티캐스트 디스커버리 문제
  (연구실 공용 WiFi에서 DDS 폭풍)를 구조적으로 우회한다. 이건 리눅스 데스크톱
  사용자도 부러워하는 속성 — E.5-2(doctor 탈-맥 확장)와 시너지.

## 확정 토폴로지 (D15, R0에서 확정 2026-07-09)

```
맥 (RoboStack, ROS_LOCALHOST_ONLY=1)
  └─ mac bridge ── -e tcp/127.0.0.1:7447 ──→ VM bridge (기존)
              └── -e tcp/<robot-ip>:7447 ──→ robot bridge (신규)
로봇 (임의 리눅스 + 임의 rmw): zenoh-bridge-ros2dds -l tcp/0.0.0.0:7447
```

- 맥이 항상 접속 주체(클라이언트) — 로봇 방화벽은 인바운드 7447 하나만 열면 됨.
- 로봇 쪽 DDS는 로봇 내부에 갇힌다(브리지가 경계) — VM과 동일한 격리 모델.
- VM↔로봇 트래픽은 맥 브리지가 zenoh 피어 라우팅으로 중계할 것으로 예상 —
  **R1에서 실측 확인 필수** (안 되면 VM 브리지에도 로봇 엔드포인트 추가하는 안으로 폴백).

## 미리 아는 리스크 / 제약

| # | 리스크 | 대응 |
|---|---|---|
| 1 | zenoh 브리지 버전 호환 — 맥은 1.9.0 핀(D7), 로봇에 다른 버전이 돌 수 있음 | 같은 마이너 버전 설치를 가이드로 강제. R1에서 버전 불일치 시 증상 실측해 doctor 처방 문구에 반영 |
| 2 | ROS_DOMAIN_ID 불일치 → 무증상 단절 | 브리지는 자기 도메인만 본다. 로봇 설치 가이드에 domain_id 명시 + doctor C16이 "링크는 살았는데 토픽 0" 패턴 감지 |
| 3 | 배포판 혼합(맥 Humble ↔ 로봇 Jazzy 등) 메시지 타입 해시 불일치 | v1 스코프는 **동일 배포판(Humble)만 지원 선언**. 혼합은 능력 매트릭스에 "미검증"으로 기재 |
| 4 | WiFi 대역폭/지연 — 카메라 등 대용량 토픽 | R1에서 ddsperf/이미지 토픽 실측 → 능력 매트릭스에 수치 기재. zenoh `--allow/--deny` 토픽 필터를 config로 노출(R2)해 불필요 토픽 차단 |
| 5 | 보안 — LAN 평문 TCP | v1은 "신뢰 LAN 전용" 명시(README). TLS(zenoh 지원)는 백로그 |
| 6 | 로봇 프로비저닝 범위 크리프 | **비목표 선언**: rosmac은 로봇에 아무것도 설치하지 않는다. 설치는 복붙 가능한 가이드 문서(1스크립트)로 제공, 실행은 사용자 |
| 7 | ROS_LOCALHOST_ONLY 불일치 → 무증상 단절 (R3 실측 발견: 노드=1, 브리지=미설정이면 로컬 디스커버리 자체가 안 됨) | 가이드 사전조건 + journalctl `Discovered` 확인 절차 + 2.1절 복붙 처방(drop-in override). doctor C16 WARN 처방 문구에 domain_id와 함께 포함(R4) |

## 단계별 계획

### R0 — 설계 확정 + D15 기록 — ✅ 완료 (2026-07-09)

- **작업**:
  1. 위 토폴로지·비목표(로봇 무설치, 동일 배포판, 신뢰 LAN)를 PLAN.md 결정
     로그에 **D15**로 기록 (근거: 단일 TCP 경계 모델의 대칭 확장). — 완료
  2. config 스키마 **확정**: `robot: {host: str|null = null, port: int = 7447,
     allow: str|null = null, deny: str|null = null}` — host가 null이면 기능
     전체 무효(기존 사용자 무영향, E.7 핀 마이그레이션과 충돌 없음).
  3. CLI 표면 **확정**: 신규 서브커맨드 없음 — `rosmac up`이 robot.host 설정 시
     엔드포인트 추가, `rosmac status`/`ps`/`doctor`가 로봇 링크 표시.
     (별도 `rosmac robot …`은 과잉 — 상태가 늘 뿐)
- **AC**: [x] PLAN.md에 D15 행 [x] 이 문서의 "확정" 표시 갱신

### R1 — 스파이크: 대리 로봇 실측 — ✅ 완료 (2026-07-09, 결과 `~/rosmac_spike/e15/results.md`)

> **결과 요약**: 6항 전부 실측 완료. ① 개통 PASS ② 트랜지티브 라우팅 **PASS —
> D15 토폴로지 유지, 폴백 불필요** ③ 서비스: 로봇이 순정 fastrtps면 호출 전부
> 타임아웃(KI-16의 로봇 확장) → **가이드에 cyclonedds 필수 명기**, cyclonedds로 정상
> ④ 10.0MB/s@10Hz 무드랍, RTT avg 0.8ms(lo 기반) ⑤ 로봇 브리지 사망 시 무오류
> 침묵 → 재기동 시 맥 무개입 자동 재접속 (doctor C16 판정 근거 확보) ⑥ 1.9↔1.8
> 상호운용 정상. 추가 발견: 비정상 종료(-9) 서버의 리스 만료가 살아있는 새 서버
> 라우트까지 retire(이름 단위 추적) — 가이드에 정상 종료 재기동 명기.
> **부수 대성과: 측정 중 KI-28 자연 재발 → 4차 조사로 원인 확정**(lima UDP 특정주소
> 하이잭, NECP 반증, 무재부팅 처방 확립 — known-issues.md, 파생 태스크 E.16).
> 대리 로봇 VM은 rosmac-spike 재사용(E.15 이전 자산이라 삭제 대신 stop 보존).

- **대리 로봇**: 제2 Lima VM (`limactl start --name=e15robot` — Ubuntu 22.04,
  기존 rosmac VM 프로비저닝 스크립트에서 브리지 설치 부분만 수동 재사용).
  실제 LAN IP 대신 lima 포트포워드(호스트 다른 포트, 예: 7457)로 "원격" 모사.
  주의: 절대 규칙 7 — 스파이크 종료 시 `limactl delete e15robot`은 이 문서가
  명시하는 지점(R1 완료 후)에서만.
- **측정 항목** (전부 `~/rosmac_spike/e15/results.md`에 기록):
  1. 맥 브리지에 `-e` 2개(기존 VM + e15robot)로 수동 기동 → 맥에서
     `ros2 topic echo` 로 로봇 talker 수신 (기본 개통)
  2. **VM↔로봇 트랜지티브 라우팅**: VM의 listener가 로봇 talker를 받는지.
     안 되면 폴백 토폴로지(VM 브리지에도 엔드포인트 추가) 실측 후 D15 보강
  3. 서비스/액션 왕복 (add_two_ints, 가능하면 fibonacci)
  4. 대역·지연: ddsperf 1MB@10Hz + RTT — VM 경유 실측(10.3MB/s)과 비교 기준
  5. 고장 모드: 로봇 브리지 kill → 맥 쪽 증상(로그·토픽 소실 시간) / 재기동 시
     자동 재접속 여부 (zenoh 재연결 동작 확인 — doctor C16 설계 입력)
  6. 브리지 버전 불일치(가능하면 1.8.x 하나 받아서) 증상 1회
- **AC**: [ ] results.md에 6항 실측 [ ] 트랜지티브 라우팅 가/부 확정
- **실패 시 대응**: 개통 자체가 안 되면 zenoh 로그 레벨 올려 세션 수립/라우트
  광고 단계 중 어디서 끊기는지 분리. 2회 실패 시 사용자 보고(스파이크 결과와 함께).

### R2 — config + up/down/status 통합 — ✅ 완료 (2026-07-09)

- **구현**: ① config.py `RobotConfig`(host/port/allow/deny, pydantic 검증 —
  잘못된 host/port는 ConfigError=exit 2) ② bridge.py `build_args(cfg)`로 인자
  구성 분리(+`robot_endpoint`, `running_cmdline`) ③ up: 로봇 링크 TCP 도달성
  확인(WARN 전용, up 비차단) + **엔드포인트 드리프트 감지**(브리지가 robot 설정
  전에 떠 있으면 재시작 안내 — E.10의 선행 구현) ④ status: Robot 행
  (not configured/reachable/unreachable).
- **개통 확인 방식**: TCP 도달성 프로브로 확정 (zenoh 세션 검증 아님 — 주석
  명시, C16에서 확장). 로봇 유래 allow/deny가 브리지 전역 필터임을 config 주석에 명시.
- **AC**: [x] robot 미설정 시 무영향 — 71 tests green(+10 신설), ruff/mypy clean
  [x] 대리 로봇 실측: up→"robot endpoint reachable"→echo /robot_chatter 수신,
  status "reachable", 드리프트 경고·unreachable WARN(exit 0) 실측
  [x] `host: tcp/bad:host` → exit 2 실측

### R3 — 관찰 통합: ps + 로봇 설치 가이드 — ✅ 완료 (2026-07-09)

- **작업** (완료):
  1. `rosmac ps`: 로봇 유래 발행자는 예상대로 그래프에서 구분 불가 → "Robot link"
     섹션 신설 — 엔드포인트 + TCP 도달성 + **브리지 인자 반영 여부**(드리프트 시
     경고, 순수 함수 `robot_link_status`로 분리해 유닛 테스트). robot 미설정이면
     섹션 자체 생략. TCP 프로브는 `bridge.robot_reachable()`로 이동(cli/psview 공용).
  2. `docs/robot-setup.md` + `robot-setup.ko.md`: 아키텍처별(aarch64/x86_64)
     다운로드+sha256 검증+systemd 유닛 1스크립트, 사전조건 체크리스트(cyclonedds
     RMW 필수·domain_id·**ROS_LOCALHOST_ONLY 일치**·방화벽·신뢰 LAN), 운영 노트
     (SIGTERM 재시작·전역 필터·버전 호환·대역 참고치). x86_64 zip sha256 신규 실측
     (`91aa0d…`).
- **AC**: [x] 가이드 스크립트를 마커로 **그대로 추출**해 대리 로봇에서 실행 →
  sha256 OK, systemd active, 7447 LISTEN. 이때 **리스크 7 실측 발견**(talker=
  localhost-only, 브리지 유닛=미설정 → 디스커버리 무증상 실패, echo 무수신) →
  가이드에 2.1절(drop-in override) 추가 후 그 블록도 그대로 실행 → talker
  Discovered → 맥에서 `ros2 topic echo /robot_chatter --once` 수신(`Hello World:
  1574`). 맥 브리지는 로봇 브리지 교체(수동→systemd)에 무개입 자동 재접속.
  [x] ps "Robot link" 섹션 실측: `tcp/127.0.0.1:7457  reachable ✓  in bridge
  args ✓`. 72 tests green(+1), ruff/mypy clean.
- **메모**: 가이드 검증 절차에 journalctl `Discovered` 확인을 추가한 것이 리스크
  7의 1차 방어선. R4의 C16 WARN 처방 문구에 domain_id + localhost-only 둘 다 포함할 것.

### R4 — doctor C16 + report 반영 — ✅ 완료 (2026-07-09)

- **작업** (완료):
  1. C16RobotLink 구현 — 판정 사다리: 미설정 → **SKIP**(CheckResult에 SKIP 상태
     신설, dim 표시, exit 무영향) / TCP 도달 불가 → **FAIL**(처방: 전원·방화벽
     7447·가이드 링크) / 도달인데 브리지 인자에 로봇 엔드포인트 없음 → **WARN
     드리프트**(down --keep-vm && up) / 도달+인자인데 브리지 로그의 zenoh 세션
     수 < 기대치(VM 가동 시 2) → **WARN 핸드셰이크 누락**(로봇 journalctl·버전
     핀 처방) / 정상 → **PASS**. 세션 수는 순수 함수 `count_bridge_sessions`
     (재접속 id 중복 dedup, 유닛 테스트).
  2. **"세션 수립인데 토픽 0" 판정은 실패 시 대응대로 백로그** — 실측 근거:
     브리지 로그의 세션 id(`New ROS 2 bridge detected: <id>`)가 엔드포인트에
     귀속 불가 → idle VM(발행자 0)과 domain 불일치 로봇을 구분할 수 없음.
     **실측 확인**: 로봇만 ROS_DOMAIN_ID=42로 바꿔도 C16은 PASS (zenoh 세션은
     domain 무관). 이 고장 모드의 방어선은 가이드의 journalctl `Discovered`
     검증 절(리스크 2·7 처방 포함).
  3. report: 번들 **전체**(config.yaml/doctor.json/로그 tail 포함)에
     `mask_host()` 일괄 적용 — 브리지 로그 cmdline/Config 덤프에도 로봇
     엔드포인트가 찍히므로 파일별 파싱 대신 전면 치환(과마스킹이 안전한 방향).
     versions.txt에 `robot: configured (host masked, port N) | not configured` 행.
- **AC**: [x] 5상태 실측 — SKIP(host null) / PASS(4 세션) / FAIL(스파이크 VM
  정지, doctor exit 1) / WARN 드리프트(로봇 켠 채 브리지만 robot 없이 재기동) /
  WARN 핸드셰이크(로봇 포트를 ssh 포트로 지정 — TCP는 열리나 세션 1<2).
  domain 42 실측은 위 2의 한계 확인. [x] report 번들 추출 후 전 파일 grep —
  호스트 문자열 0건, config.yaml `host: masked-by-report`. 81 tests green(+9),
  ruff/mypy clean.
- **메모**: ① 스파이크 VM 정지 직후 C8이 일과성 FAIL(재실행 PASS) — 브리지
  세션 정리 중 타이밍으로 추정, 재발 시 조사. ② 로봇 VM 재부팅에서 가이드
  유닛의 systemd enable 자동 기동 확인(재부팅 시나리오 검증 덤). ③ C15 번호는
  E.10(config 드리프트)에 예약.

### R5 — 실기 검증 게이트 — ⏸ 잠정 보류 (2026-07-09 사용자 결정: 실기 없음)

- **전제**: 실로봇 또는 RPi+ROS 2 Humble 1대. 없으면 이 단계만 무기한 보류 —
  R0~R4 완료 상태로 "beta (surrogate-verified)" 라벨로 능력 매트릭스에 기재 가능.
- **대안 경로** (사용자 안내 완료): 로봇이 아니어도 같은 WiFi의 리눅스 머신
  (남는 노트북 Ubuntu+Humble, 두 번째 맥 등)이면 핵심인 무선 구간 실측은 가능.
- **작업**: robot-setup.md를 실기에서 그대로 수행 → 개통, teleop급 왕복(cmd_vel
  주기 발행 + odom 수신), WiFi 실측(대역·RTT·끊김 후 재접속), 결과를 이 문서와
  능력 매트릭스에 기록. 실기에서만 나오는 함정은 KI로 등록.
- **AC**: [ ] 실기 개통 스크린샷/로그 [ ] WiFi 실측 수치 [ ] "beta" 라벨 해제

### R6 — 문서/포지셔닝 마감 — ✅ 완료 (2026-07-09)

- **작업** (완료): README(en/ko) — 커맨드 표 불변 확인(신규 커맨드 없음),
  아키텍처 다이어그램에 robot 분기(⇢ 선택 행), 능력 매트릭스(E.14)에
  "Robot link (LAN) 🧪 beta" 행(대리 로봇 실측 수치 + R5 링크 + **신뢰 LAN
  전용 평문 TCP 고지**). workflow.md(en/ko) "4. 실로봇 연결 (beta)" 절.
  CHANGELOG 0.1.0에 실로봇(beta)·능력 매트릭스 항목 (+Phase 5 doctor --fix/
  report 누락분 소급).
- **AC**: [x] 영/한 문서 정합 (다이어그램·매트릭스·workflow 절·가이드 모두
  양언어 동일 구조) [x] E.14 매트릭스에 robot 행 — 실측 근거(10 MB/s·RTT<1ms·
  자동 재접속)와 e15 계획 문서 링크 포함
- **메모**: R5 보류로 "beta (surrogate-verified)" 라벨 유지 — 라벨 해제 조건은
  R5 실기 실측.

## E.14와의 순서

E.14(능력 매트릭스 실측: parameters/rosbag)를 **먼저** 하는 것을 권장 — R1 스파이크가
같은 측정 인프라(브리지 경유 실측)를 쓰므로, E.14에서 만든 측정 절차를 R1이 재사용하고,
매트릭스 표에 robot 열을 나중에 붙이는 흐름이 중복이 없다.

## 백로그 (이 계획의 비목표)

- zenoh TLS/인증 (리스크 5)
- 다중 로봇(robot을 리스트로) — 스키마는 v1에서 단수로 두되 마이그레이션 쉬움
- 배포판 혼합 지원 (리스크 3)
- 로봇 쪽 원격 프로비저닝/업데이트 (비목표 선언 유지)

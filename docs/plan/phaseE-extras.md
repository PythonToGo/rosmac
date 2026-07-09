# E 트랙 — 상품성 점검(2026-07-08~09) 파생 태스크

> 출처: Run F(CI) 착수 전 상품성·완비성 점검 (경쟁 조사 결론·수리 내역은
> [phase5-results.md](phase5-results.md) "부수 작업 — 상품성 점검" 절).
> **전부 비게이트** — Phase 5→6 진행을 막지 않으며, 개별 착수/생략 가능.
> 이미 완료된 수리(LICENSE, pyproject 메타데이터, README 영어 메인+한국어)는
> 여기 없음 — 커밋 `27d4a21` 참조.

## E.1 docs/workflow.md 영어 메인 + 한국어 병행 — ✅ 완료 (2026-07-09)

- **배경**: README를 영어 메인(README.md)+한국어(README.ko.md)로 개편했는데,
  README가 링크하는 workflow.md(개발 루프·pick_demo 예제)는 아직 한국어뿐 —
  외부 사용자 여정이 Quickstart 다음 단계에서 끊긴다.
- **작업**: workflow.md를 영어로 전환, 한국어는 workflow.ko.md로 분리, 양쪽
  README에서 각각 링크. 코드 블록·실측 값은 불변.
- **AC**: [x] 영어 workflow.md + 한국어 workflow.ko.md 상호 링크 (커밋 c2c179e —
  코드블록 바이트 동일·다이어그램 정렬 보존 검증)
  [x] 명령·출력 예시가 현행 CLI(영어 출력)와 일치

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

## E.6 LICENSE 저작권자 표기 확인 — ✅ 완료 (2026-07-08)

- **배경**: LICENSE 신설 시 "Copyright (c) 2026 Taeyoung Kim"으로 기재 —
  표기(실명/핸들/병기)는 사용자 결정 사안.
- **AC**: [x] 사용자 확인 — "그대로" (2026-07-08, push 전 확정)

---

# 2차 점검 (2026-07-09) 파생 — 기능·구조·OSS 3방향 조사 결과

> 조사 방법: 병렬 감사 3건 (OSS 커뮤니티 인프라 / 기능 갭 — 코드 실측 근거 포함 /
> 코드 구조 리뷰 — 13모듈 2,457줄 전수). 이미 Phase 5.5/6/7에 계획된 항목은 제외.

## E.7 [배포 전 필수] rosmac 업그레이드 경로 — 핀 마이그레이션

- **배경 (실측)**: config.load()가 첫 실행 때 브리지 버전/sha 전체를
  `~/.rosmac/config.yaml`에 동결(config.py:64-69)하고 `ensure_binary`는 존재만
  검사(bridge.py:33-35) → pip 업그레이드해도 구버전 브리지/구 config로 조용히
  동작. **P5.5 배포 직후 첫 릴리스부터 전 사용자가 밟는 지뢰** — 0.y "minor may
  break" 선언과 정면 충돌.
- **작업**: ① config에 사용자 미수정 핀은 코드 기본값을 따르게 (저장 시 핀 제외
  또는 버전 스탬프+마이그레이션) ② ensure_binary 버전 비교 후 재다운로드
  ③ (같은 파일) bridge 다운로드 `urlretrieve` → timeout 있는 urlopen 스트리밍
  (무한 대기 가능한 유일한 네트워크 호출 — 구조 리뷰 B6)
- **AC**: [ ] 구 config + 신 코드에서 `rosmac up`이 신 핀 사용 실측
  [ ] 핀 갱신 릴리스 시나리오 유닛 [ ] 다운로드 타임아웃 존재
- **시점**: **P5.5 착수 전** (게이트급)

## E.8 `rosmac logs` — 로그 열람 커맨드

- **배경**: doctor/에러 메시지 3곳이 이미 로그를 가리키는데(bridge.log, VM
  journalctl) 열람 커맨드가 없어 사용자가 원시 명령을 쳐야 함. 로그는 3곳 분산.
- **작업**: `rosmac logs [--vm] [--foxglove] [-f/--follow] [-n N]` — 맥 브리지
  tail 기본, --vm은 journalctl -u zenoh-bridge 위임.
- **AC**: [ ] 세 소스 각각 열람 실측 [ ] -f 동작 [ ] doctor remedy 문구를
  `rosmac logs`로 교체
- **가치×난이도**: 상×소 (반나절)

## E.9 `init --recreate-env|--recreate-vm` + 디스크 프리플라이트

- **배경**: env/VM 존재 시 무조건 skip(cli.py) → 반쯤 깨진 env의 탈출로가 전체
  uninstall(40GB 재설치)뿐. 첫 주 최다 빈도 사고. + init에 디스크 여유 사전
  체크 없음(README 40GB 요구, C11은 사후 WARN만).
- **작업**: 대상만 삭제 후 재생성하는 플래그 2종(확인 프롬프트, 절대 규칙 7) +
  init 첫 단계에 디스크 프리플라이트(부족 시 UsageError).
- **AC**: [ ] env 오염 시나리오에서 --recreate-env만으로 복구 실측
  [ ] 디스크 부족 모의에서 다운로드 전 차단
- **가치×난이도**: 상×소

## E.10 doctor C15 — config↔실환경 드리프트 감지

- **배경**: VM 리소스(cpus/memory)·domain_id는 생성 시 베이크되는데 config.yaml
  수정이 조용히 무시됨. domain_id는 맥(매 실행)/VM(베이크) 불일치 시 무증상
  디스커버리 단절 — 신뢰 파괴형.
- **작업**: C15 신설 — config vs `limactl list --json`(리소스)·VM 내
  /etc/profile.d(domain_id) 비교, 불일치 시 WARN + 처방(limactl edit 또는
  E.9 --recreate-vm).
- **AC**: [ ] config 변경 후 C15 WARN 실측 + 처방으로 해소 실측
- **가치×난이도**: 중×소

## E.11 OSS 미계획 4종 + D11 정합화

- **배경**: Phase 6 계획은 우수(감사 결과) — 계획에 아예 없는 것만:
- **작업**: ① README 배지 4종(CI·PyPI·license·python — 6.1 AC에 추가)
  ② CHANGELOG 영어화(+함정 수 28→29 정합) ③ CITATION.cff (JOSS/D13 정합,
  파일 1개) ④ dependabot.yml (github-actions+pip 월간)
  ⑤ D11("한국어 병행판 없음")과 README.ko.md 모순 → D11 개정 기록
  (영어=원본, 한국어 병행 허용 — 사용자 지시 2026-07-08)
- **AC**: [ ] 4파일 존재+배지 렌더 [ ] D11 개정 행에 사유·날짜
- **가치×난이도**: 중×소 (전부 합쳐 1시간)

## E.12 구조 부채 1차 — 싸고 지금뿐인 것들

- **배경**: 구조 리뷰 (b) 중 순수 이동·리스크 제로급.
- **작업**: ① `paths.py` 신설 — ~/.rosmac 레이아웃 지식 5개 모듈 분산 집약(B5)
  ② VM ROS env 주입 4중 복제 → `lima.vm_ros_env(cfg)` 단일화(B2, KI-19 재발 온상)
  ③ distro 하드코딩 즉효 3건: cli.py:75 리터럴, ENV_PACKAGES→`env_packages(cfg)`,
  deps map_dep 기본 인자(B3) ④ 에러 규약 명문화 — 라이브러리 레이어도
  RosmacError/UsageError 직접, `except RuntimeError`는 관찰 도구 한정 규칙을
  errors.py에 문서화 + 이중 포장 2곳 정리(B9) ⑤ 프리셋 유래 문자열(vm_apt,
  preset.name) 검증/quote(B6)
- **AC**: [ ] 61+ 테스트 green 유지 [ ] grep으로 humble 리터럴이 provision
  템플릿·프리셋에만 잔존 [ ] private 크로스 접근(conda._check 등) 0
- **가치×난이도**: 중×소~중 (반나절)

## E.13 구조 부채 2차 — cli.py 오케스트레이션 추출 (중형)

- **배경**: cli.py 729줄에 13개 커맨드 본문 인라인 — 커맨드 본문이 유닛 테스트
  불가(B1), doctor 사전점검이 표시 문자열 파싱에 결합(B7), 사용자 프리셋이
  부속 파일을 VM에 못 보냄(B8). "지금이 마지막 싼 시점" 판정.
- **작업**: ① `ops.py` 레이어 — init/up/down/viz 절차를 순수 함수로, cli는
  렌더링만 ② Check에 `id` 필드 + `doctor.run_selected(cfg, ids)` ③
  `_push_preset_assets`가 USER_PRESET_DIR도 보게 + layout 오버레이
- **AC**: [ ] up/init 절차 유닛 테스트 신설 [ ] sim 사전점검이 id 기반
  [ ] 사용자 프리셋 디렉토리의 launch 파일이 VM 전송됨 실측
- **가치×난이도**: 상×중 (1~2일) — Phase 6 전 권장 (기여자가 복제할 패턴 확정)

## E.14 브리지 능력 매트릭스 + rosbag 스토리 — ✅ 완료 (2026-07-09)

- **배경**: topics/actions는 실측 선언돼 있으나 **parameters·rosbag은 동작 여부
  기술 자체가 없음** (리포 전체 rosbag 언급 0). "VM에서 bag 녹화 → 맥에서 분석"
  루프의 파일 회수 경로도 없음 (push_tree는 단방향).
- **실측 결과** (2026-07-09, VM talker 대상):
  - **parameters = ⚠️ 부분**: 파라미터 서비스 6종 전부 브리지 라우팅 —
    `ros2 service call`로 get(값 수신)·set(successful=True) 실측. 단
    `ros2 param` CLI는 "Node not found" — 브리지가 원격 노드를 노드 그래프에
    미러링하지 않음(`ros2 node list`에 VM 노드 부재). 매트릭스에 구분 명기.
  - **rosbag2 = ✅ 전 방향**: 맥에서 VM 토픽 녹화 20/20 무손실(20s@1Hz, 단
    신규 토픽 첫 구독은 라우트 생성 수 초 — 첫 8s 실행이 1msg였던 원인),
    VM 내 녹화 9msg, VM bag 재생→맥 수신, 맥 bag 재생→VM 수신.
  - **회수 = `limactl cp -r rosmac:/tmp/vmbag ~/dest` 실측 동작 → D16**
    (`rosmac pull` 도구 보류, PLAN.md 결정 로그 기재).
- **AC**: [x] README(en/ko) "브리지 능력 매트릭스" 5행 + 실측 근거
  [x] bag 회수 절차 workflow.md(en/ko) rosbag 절 + D16
  [x] 구조적 한계 3종 README 명시 — 브리지 홉(고주파 루프 VM 완결),
  KI-28(타 lima VM 잠식, KI 링크), VM 헤드리스(D2, Foxglove가 답)
- **가치×난이도**: 중×중

## E.15 실로봇 연결 — zenoh 아키텍처의 LAN 확장 — 🧪 beta 출시 상태 (R0~R4·R6 완료, R5 보류 2026-07-09)

- **배경 (3차 점검 2026-07-09)**: 맥↔VM 폐쇄 루프라 같은 LAN의 실로봇과 연결
  경로가 없음 — "시뮬 전용" 인상을 "실로봇 개발 도구"로 바꾸는 최대 포지셔닝
  기회. 기술적으로는 자연 연장: 맥 브리지가 이미 zenoh 클라이언트(bridge.py:97),
  로봇에 브리지 하나 더 두고 `-e tcp/<robot>:7447` 추가가 골자. DDS 멀티캐스트가
  WiFi를 안 건너는 것 자체가 셀링포인트(E.5-2 시너지).
- **작업**: **상세 단계별 계획 [e15-real-robot.md](e15-real-robot.md)** —
  R0 설계(D15 기록) → R1 대리 로봇(제2 Lima VM) 스파이크 실측 → R2 config+up
  통합(신규 커맨드 없음, robot.host null이면 무영향) → R3 ps+로봇 설치 가이드
  → R4 doctor C16 → R5 실기 검증 게이트(**사용자 하드웨어 필요**, 그 전까지
  "beta" 라벨) → R6 문서 마감.
- **AC**: 단계별 AC는 계획 문서에. 전체 완료 = R6까지 + R5(실기) 또는 beta 라벨.
- **가치×난이도**: 상×중 (R0~R4 합쳐 ~4시간 + R5는 하드웨어 대기)
- **시점**: E.14 **이후** 권장 (측정 인프라 재사용 — 계획 문서 "E.14와의 순서" 절)

## E.16 doctor — 외부 lima VM UDP 하이재커 감지 (KI-28 4차 파생)

- **배경 (실측 2026-07-09)**: KI-28 원인 확정 — UDP ignore 규칙 없는 lima VM의
  hostagent가 호스트 127.0.0.1:74xx를 특정주소+REUSEADDR로 선점하면 맥 DDS
  유니캐스트가 조용히 잠식돼 디스커버리가 점진 붕괴. 현행 doctor의 lima 규칙
  체크/픽서는 **rosmac 자체 VM만** 봄 — 사용자가 다른 lima VM(구 스파이크 VM,
  docker 대체 VM 등)을 띄우면 무방비.
- **작업**: C17(가칭) — `lsof -iUDP:7400-7440`에서 DDS 외 프로세스(특히 limactl)의
  127.0.0.1 특정주소 바인드 감지 → FAIL + 처방(해당 VM lima.yaml에 ignore 규칙,
  KI-28 처방 절 링크). --fix는 외부 VM 설정 임의 수정이라 **비대상**(안내만).
  잔여 오염 정리(hang CLI + 데몬 재시작)는 기존 C8/C12 처방 문구에 반영.
- **AC**: [ ] 미수리 VM 기동 상태에서 C17 FAIL + 처방 실측 [ ] 수리 후 PASS
  [ ] KI-28 처방 절과 문구 정합
- **가치×난이도**: 상×소 (신뢰 파괴형 고장의 유일 감지 수단)

## 백로그 (미등록 관찰 — 요구 발생 시)

- `shell -c` 타임아웃 300s 하드코딩 → 옵션화 (하×소)
- 오프라인/에어갭 설치 (하×대, E.5-3 교육 시나리오와 연동)
- 멀티 프로필/제2 VM (하×중)
- 주석 언어 정책(한국어 KI 주석 유지 + CONTRIBUTING 명시 — Phase 6.3에서)

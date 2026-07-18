# E.19 실측 — RoboStack jazzy/lyrical osx-arm64 커버리지 (2026-07-18)

> 목적: E.5-4 배포판 전환 스파이크(Humble → Jazzy/Lyrical)의 go/no-go 입력.
> 방법: 채널 repodata.json 직접 계수 (conda 환경 생성 없음, 네트워크 조회만).
> 소스: `https://repo.prefix.dev/robostack-{jazzy,lyrical}/{osx-arm64,linux-64}/repodata.json`
> — jazzy는 `conda.anaconda.org/robostack-jazzy`와 교차 확인(계수 일치).
> 원본 JSON 사본: `~/rosmac_spike/e19/` (휘발 — 본 문서가 보존본).

## 채널 규모 (unique 패키지명 기준)

| 채널 | osx-arm64 | linux-64 | 비고 |
|---|---|---|---|
| robostack-jazzy | **853** | (미계수) | prefix.dev == anaconda.org (853 일치) |
| robostack-lyrical | **728** | 747 | **prefix.dev 전용** — anaconda.org는 403 Forbidden |
| robostack-kilted (참고) | 821 | — | 2026-07-10 딥리서치 계수 (deepresearch-2026-07-10-frameworks-eol.md) |

→ lyrical 채널은 "얇다" 수준이 아니라 jazzy의 85% 규모로 이미 실질 운영 중
(출시 2026-05 후 2개월 시점). 단 아래 Nav2 공백이 결정적.

## 핵심 패키지 커버리지 표 (osx-arm64, 최신 버전)

| 패키지 (`ros-<distro>-` 접두 생략) | jazzy | lyrical |
|---|---|---|
| desktop | 0.11.0 | 0.13.0 |
| desktop-full | 0.11.0 | 0.13.0 |
| moveit | 2.12.4 | 2.14.1 |
| moveit-planners | 2.12.4 | 2.14.1 |
| moveit-ros | 2.12.4 | 2.14.1 |
| navigation2 | 1.3.12 | **❌ 없음** |
| nav2-bringup | 1.3.12 | **❌ 없음** |
| slam-toolbox | 2.8.5 | **❌ 없음** |
| rmw-cyclonedds-cpp | 2.2.3 | 4.1.4 |
| foxglove-bridge | 3.3.0 | 3.4.1 |
| ros-gz / -bridge / -sim | 1.0.22 | 3.0.9 |
| (참고) nav2-* 패키지 총수 | 35 | **0** |

**짝 Gazebo** (ros-gz-sim-vendor 의존성으로 확인):
jazzy → `gz-sim8` = **Harmonic** (libgz-sim8 ≥8.10.0),
lyrical → `libgz-sim` ≥10.4.0,<11 = **Jetty** (gz-sim 10.x).
어느 쪽이든 현행 Fortress(VM)와 다르므로 전환 시 시뮬 스택도 함께 이동.

## Nav2 공백의 성격 — osx 특이가 아님

lyrical의 nav/slam 매칭 패키지는 osx-arm64·linux-64 **양쪽 모두**
`nav-msgs`, `nmea-navsat-driver` 2건뿐 — Nav2 스택(navigation2, nav2-*,
slam-toolbox)은 **채널 전체 부재**. 즉 RoboStack osx 빌드 실패가 아니라
Lyrical용 Nav2가 아직 채널에 들어오지 않은 업스트림/패키징 단계 문제
(Lyrical 출시 2026-05 직후라는 시간 요인과 정합).

## 판정 (E.5-4 스파이크 입력)

- **Jazzy 경로: 유효.** rosmac 핵심 의존 전부 osx-arm64 존재
  (MoveIt 2.12 LTS = moveit.ai 공식 권장 트랙, Nav2 1.3.12 풀스택 35개,
  cyclonedds·foxglove-bridge·ros-gz@Harmonic).
- **Lyrical 직행: 현시점 불가.** Nav2 스택 부재로 E.17 nav2-diffbot 프리셋을
  이식할 수 없음. MoveIt(2.14.1)·기타 코어는 이미 존재하므로 Nav2 채널 유입
  시 재평가 — 전환 착수 전 본 계수 재실행으로 확인.
- **운영 주의**: lyrical 채널은 prefix.dev 전용(anaconda.org 403) —
  전환 시 rosmac의 채널 URL 처리에 소스 분기 필요.

## 재현 커맨드

```sh
curl -sL https://repo.prefix.dev/robostack-lyrical/osx-arm64/repodata.json -o ly.json
jq -r '(.packages + ."packages.conda") | [.[].name] | unique | length' ly.json
jq -r '(.packages + ."packages.conda") | [.[] | select(.name=="ros-lyrical-moveit") | .version] | unique' ly.json
jq -r '(.packages + ."packages.conda") | [.[].name] | unique | .[] | select(test("nav|slam"))' ly.json
```

# 딥리서치 최종 보고 — ROS 2 프레임워크 지형 / MoveIt 범위 / Humble EOL 로드맵 / rosmac 적용성

> 실행: 2026-07-10, deep-research 워크플로 (5각도 검색 → 소스 41건 → 주장 37건 3표 적대 검증 → 종합).
> 1차 실행이 네트워크 단절로 중단 → 저널 복원 후 continuation 워크플로로 완료
> (캐시 투표 67 + 신규 투표 61, 에이전트 62, 에러 0).
> 판정: **37개 주장 → 35 확정 / 2 반박 / 0 미검증**. 반박 2건은 낡은 배포판 목록이 섞인
> 부정확 버전이며 동일 내용의 정확한 버전이 별도 확정 — 결론 영향 없음.

## 연구 질문

ROS 2 생태계에서 MoveIt 외 주요 프레임워크(Nav2 등)와 각 용도, MoveIt의 실제 범위(모션 플래닝 전용 여부), ROS 2 Humble EOL(2027-05) 이후 선택지(Jazzy/Kilted/Rolling 등 LTS 로드맵), 그리고 rosmac 아키텍처(macOS RoboStack + Lima VM Ubuntu 22.04 + zenoh 브리지, Humble 고정 D1)에 다른 배포판/프레임워크를 추가할 수 있는지 평가

## 요약

ROS 2 생태계의 공식 '대형 커뮤니티 프로젝트'는 ros2_control, Navigation2(Nav2), MoveIt, micro-ROS 4개이며, Nav2는 모바일 로봇 내비게이션, MoveIt은 매니퓰레이션 도메인을 담당하는 명확히 분리된 프레임워크다. MoveIt은 모션 플래닝 전용 라이브러리가 아니라 기구학, 제어(궤적 실행), 충돌 검사, 3D 인식(Octomap), 태스크 수준 플래닝(MTC), 하이브리드 플래닝까지 포괄하는 매니퓰레이션 플랫폼이지만, 내비게이션(코스트맵 레이어 등)은 명시적으로 범위 밖이며 Nav2와 경쟁이 아닌 상호보완(nav2_simple_commander 연동) 관계다. Humble은 2027년 5월 EOL이며, 이후 LTS 선택지는 Jazzy(EOL 2029-05, Ubuntu 24.04 Tier 1)와 Lyrical Luth(2026-05 출시 LTS, EOL ~2031-05, Ubuntu 26.04 Tier 1)이고, Kilted는 non-LTS(EOL 2026-11)라 장기 후속 대안이 아니다. rosmac 아키텍처 기준으로 mac 측 RoboStack은 jazzy/kilted/lyrical/rolling 채널과 osx-arm64 빌드를 이미 제공해 동일 패키징 생태계 내 업그레이드 경로가 존재하지만, Lima VM 측은 배포판당 단일 Ubuntu LTS만 Tier 1 지원되므로 Humble 이후 배포판 추가 시 VM 베이스 이미지 교체(22.04→24.04 또는 26.04)가 필수다. Nav2 등 다른 프레임워크 추가 자체는 Humble 고정(D1) 상태에서도 가능하나, zenoh 브리지의 이기종 배포판 간 호환성과 osx-arm64 패키지 커버리지는 별도 검증이 필요하다.

## 확정 findings (9건)

### F1 (high) — 투표 6-0, 6-0, 3-0 (3개 클레임 병합)

ROS 2 공식 문서가 인정하는 '대형 커뮤니티 프로젝트'는 정확히 4개 — ros2_control, Navigation2(Nav2), MoveIt, micro-ROS — 이며, Nav2는 모바일 로봇용 내비게이션 스택으로 MoveIt(매니퓰레이션)과 도메인이 분리된 프레임워크다.

**근거**: 공식 문서: "Navigation2 (nav2.org): Comprehensive and flexible navigation stack for mobile robots using ROS 2." Nav2 메인테이너의 동료심사 논문(Robotics and Autonomous Systems 2023): "Nav2 is the major project within the mobile robotics ecosystem and provides a next-generation autonomous mobile robotics navigation framework and system." Humble/Rolling 문서 모두 'Large Community Projects' 섹션에 ros2_control, Navigation2, MoveIt, micro-ROS 4개만 나열함이 원문(ros2_documentation 저장소)에서 검증됨.

**소스**:
- https://docs.ros.org/en/humble/Related-Projects.html
- https://docs.ros.org/en/rolling/Related-Projects.html
- https://arxiv.org/pdf/2307.15236

### F2 (high) — 투표 6-0 외 다수 3-0 (8개 클레임 병합)

MoveIt은 모션 플래닝 전용 라이브러리가 아니다. 공식적으로 '매니퓰레이션 애플리케이션 플랫폼'으로 정의되며 모션 플래닝, 매니퓰레이션(파지 생성), 역기구학, 제어(궤적 실행), 3D 인식(Octomap), 충돌 검사 6대 기능을 포괄하고, ROS-Industrial의 핵심 모션 플래닝 라이브러리이기도 하다.

**근거**: ROS 2 공식 문서: "A rich platform for building manipulation applications featuring advanced kinematics, motion planning, control, collision checking, and much more." moveit.ai는 6대 기능(Motion Planning, Manipulation, Inverse Kinematics, Control, 3D Perception, Collision Checking)을 명시. GitHub 저장소: "Easy-to-use open source robotics manipulation platform for developing commercial applications, prototyping designs, and benchmarking algorithms." 동료심사 논문: "MoveIt is the primary software library for motion planning and mobile manipulation in ROS ... the core motion planning library for ROS-Industrial." 단, 공식 문구의 'control'은 ros2_control을 대체하는 것이 아니라 하위 컨트롤러로의 궤적 실행을 의미하며, 'navigation' 언급은 마케팅 잔재로 실제 베이스 내비게이션 기능은 없음.

**소스**:
- https://docs.ros.org/en/humble/Related-Projects.html
- https://moveit.ai/
- https://github.com/moveit/moveit2
- https://moveit.picknik.ai/humble/index.html
- https://www.sciencedirect.com/science/article/pii/S0736584523000352

### F3 (high) — 투표 6-0, 3-0 x4 (5개 클레임 병합)

MoveIt의 범위는 단일 궤적 플래닝을 넘어선다: PointCloud/깊이 데이터를 소비해 충돌 검사용 점유 맵(Octomap)을 만드는 인식 파이프라인, RViz 핸드아이 캘리브레이션 도구(moveit_calibration), 다단계 태스크(픽앤플레이스)를 스테이지로 구성하는 MoveIt Task Constructor(MTC), 그리고 동적 환경에서 전역+지역 플래너를 결합해 반응형 재플래닝을 수행하는 Hybrid Planning 아키텍처를 포함한다.

**근거**: 공식 튜토리얼: "MoveIt Task Constructor provides a way to plan for tasks that consist of multiple different subtasks (known as stages)." Hybrid Planning 문서: "enables reactive re-planning in dynamic or unknown environments." 워크숍 자료: "Occupancy map for collision checking. Update from depth map or point cloud." 단, MTC는 코어 MoveIt에 번들되지 않은 별도 설치 패키지(moveit 조직 산하)이고, Hybrid Planning은 튜토리얼 수준으로 프로덕션 채택도는 낮은 편.

**소스**:
- https://moveit.ai/events/rosworld-2021-workshop/MoveIt%20and%20the%20rest%20of%20ROS_%20Perception,%20Control,%20and%20Simulation%20ROSWorld%20October%202021%20-%20Mobile%20Manipulation%20Workshop.pdf
- https://moveit.picknik.ai/humble/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html
- https://moveit.picknik.ai/humble/doc/examples/hybrid_planning/hybrid_planning_tutorial.html

### F4 (high) — 투표 6-0, 5-0 (2개 클레임 병합)

MoveIt은 명시적으로 내비게이션 프레임워크가 아니다: 인플레이션 레이어 같은 내비게이션 코스트맵 레이어를 지원하지 않으며 메인테이너가 'navigation2를 대체하려는 것이 아니다'라고 명시했다. 두 프레임워크는 경쟁이 아닌 상호운용 관계로, MoveIt이 생성한 베이스 웨이포인트를 nav2_simple_commander API로 Nav2에 넘겨 실행시키는 패턴이 공식적으로 제시되며, 모바일 매니퓰레이션은 두 프레임워크의 명시적 통합으로 구현한다.

**근거**: 워크숍 PDF 원문(다운로드 후 텍스트 추출로 검증): "MoveIt 2 does not support navigation layers and is not meant to be a replacement for navigation2." 및 "Using nav2_simple_commander we can give the MoveIt generated waypoints and let nav2 execute the trajectory for us instead of MoveIt if desired." 2025년 PickNik의 MoveIt Pro + Nav2 통합 발표도 대체가 아닌 통합 패턴을 재확인.

**소스**:
- https://moveit.ai/events/rosworld-2021-workshop/MoveIt%20and%20the%20rest%20of%20ROS_%20Perception,%20Control,%20and%20Simulation%20ROSWorld%20October%202021%20-%20Mobile%20Manipulation%20Workshop.pdf
- https://arxiv.org/pdf/2307.15236

### F5 (high) — 투표 3-0 x7 (7개 클레임 병합)

ROS 2 릴리스 로드맵: 매 12개월 릴리스, 짝수 해 LTS(약 5년 지원)·홀수 해 non-LTS(1.5년 지원) 교대. Humble Hawksbill: 2022-05~2027-05 EOL(Ubuntu 22.04 Tier 1). Jazzy Jalisco: 2024-05~2029-05 LTS(Ubuntu 24.04 Tier 1). Kilted Kaiju: 2025-05~2026-11 non-LTS. Lyrical Luth: 2026-05 출시 LTS, EOL ~2031-05. M Turtle(2027-05, non-LTS), N Turtle(2028-05, LTS). 따라서 Humble EOL(2027-05) 시점의 가용 LTS는 Jazzy와 Lyrical이며, Kilted는 그 전(2026-11/12)에 이미 EOL이라 장기 후속 대안이 아니다.

**근거**: REP-2000 원문: "Humble Hawksbill (May 2022 - May 2027)", "Jazzy Jalisco (May 2024 - May 2029)", "Kilted Kaiju (May 2025 - November 2026)". 공식 릴리스 스케줄: "May 2026: Lyrical Luth: LTS release, supported for 5 years / May 2027: M Turtle: non-LTS / May 2028: N Turtle: LTS". endoflife.date 교차 확인 완료(Lyrical 2026-05-22 출시, EOL 2031-05-31). Kilted EOL은 REP-2000 기준 2026-11, endoflife.date 기준 2026-12로 1개월 차이 존재.

**소스**:
- https://reps.openrobotics.org/rep-2000/
- https://docs.ros.org/en/humble/The-ROS2-Project/Release-Schedule.html

### F6 (high) — 투표 3-0 x3 (검증자 정정 반영 병합)

각 ROS 2 배포판은 정확히 하나의 Ubuntu LTS만 Tier 1 완전 지원한다(구버전 Ubuntu는 최대 Tier 3 소스 빌드). 따라서 rosmac의 Ubuntu 22.04 고정 Lima VM(D1)은 Jazzy/Kilted(Tier 1 = 24.04)나 Lyrical(Tier 1 = 26.04)을 공식 바이너리로 호스팅할 수 없으며, Humble 이후 배포판을 추가하려면 배포판별로 VM 베이스 이미지 교체(22.04→24.04→26.04)가 필요하다.

**근거**: 공식 문서: "A single ROS 2 distribution will only have full Tier 1 support for a single Ubuntu LTS. ... On a case-by-case basis, a ROS 2 distribution may support an older Ubuntu LTS distribution as a Tier 3, community-supported platform." REP-2000 표: Jazzy Tier 1 = Ubuntu Noble(24.04), 22.04는 Tier 3 소스 빌드만; Kilted는 22.04 지원 없음. 검증자 정정 사항: 원 클레임의 'Lyrical도 24.04'는 오류로, Lyrical Luth의 Tier 1은 Ubuntu 26.04(Resolute)임 — 이는 배포판 업그레이드마다 VM 이미지 교체가 필요하다는 결론을 오히려 강화함.

**소스**:
- https://reps.openrobotics.org/rep-2000/
- https://docs.ros.org/en/humble/The-ROS2-Project/Release-Schedule.html

### F7 (high) — 투표 3-0 x7 (7개 클레임 병합)

MoveIt 2는 Humble(2.5 LTS, 'Maintained'), Jazzy(2.12 LTS, 'Latest Stable - Recommended'), Kilted(안정 브랜치), Rolling(2.13, main 브랜치)을 배포판별 브랜치로 지원한다. Humble 브랜치는 버그 백포트만 받는 유지보수/동결 상태이고 문서에도 'not being developed further' 배너가 표시되며, MoveIt 프로젝트의 공식 권장 마이그레이션 대상은 Jazzy LTS다. 즉 rosmac은 현재 유지보수되는 MoveIt 릴리스를 보유하고 있고, Humble 이후 배포판에도 MoveIt 지원이 이미 존재한다.

**근거**: moveit.ai 릴리스 표(2026-07 실시간 확인): "Rolling 2.13 CONTINUALLY DEVELOPED / Jazzy 2.12 LTS LATEST STABLE - RECOMMENDED / Humble 2.5 LTS MAINTAINED / Iron·Galactic·Foxy EOL - DISCONTINUED". GitHub README 브랜치 정책: main은 rolling 빌드팜에만 배포, humble/jazzy/kilted는 배포판별 안정 브랜치(버그 백포트만). Humble 문서 배너: "You're reading the documentation for a stable version of MoveIt that is not being developed further." ROS Index에서 Humble/Jazzy/Kilted/Rolling 바이너리 릴리스(2.14.x) 확인됨.

**소스**:
- https://moveit.ai/
- https://github.com/moveit/moveit2
- https://moveit.picknik.ai/humble/index.html

### F8 (high) — 투표 3-0 x3 (3개 클레임 병합)

rosmac의 mac 측(RoboStack) 레이어는 Humble 이후로의 직접적 업그레이드 경로가 존재한다: RoboStack은 robostack-humble 외에 robostack-jazzy, robostack-kilted, robostack-lyrical, robostack-rolling(그리고 ROS 1 noetic) conda 채널을 공식 제공하며, osx-arm64(Apple Silicon)를 지원 플랫폼에 포함하고, ros-jazzy 레시피 저장소는 활발히 유지보수 중(~1,600+ 커밋, macOS/ARM64 CI)이다. 따라서 새 배포판 추가는 동일 패키징 생태계 안에서 가능하다.

**근거**: 공식 문서: "ROS 2: Humble (robostack-humble), Jazzy (robostack-jazzy), Kilted (robostack-kilted), Lyrical (robostack-lyrical), Rolling (robostack-rolling)", 플랫폼 목록에 osx-arm64 포함. anaconda.org에서 robostack-jazzy 패키지가 2026-06까지 갱신되고 macOS-arm64 지원 확인. 실사용 근거: RoboStack/ros-jazzy issue #124에서 M3 Mac 네이티브 구동 사례. 단, 배포판·플랫폼별 패키지 커버리지는 완전 동등하지 않음(특히 Kilted의 osx-arm64에 누락 패키지 존재) — MoveIt/Nav2 등 특정 패키지는 마이그레이션 전 개별 확인 필요.

**소스**:
- https://robostack.github.io/GettingStarted.html
- https://github.com/RoboStack/ros-jazzy

### F9 (medium) — 투표 합성 (직접 검증 클레임 아님)

종합 평가(합성): rosmac 아키텍처에 다른 프레임워크(Nav2 등)를 추가하는 것은 현 Humble 고정(D1) 상태에서도 원리적으로 가능하다 — Nav2는 Humble을 포함한 활성 배포판에서 지원되는 별도 스택이며 MoveIt과 충돌하지 않는다. 반면 다른 '배포판' 추가는 양측 비대칭이다: mac 측 RoboStack은 채널 교체로 대응 가능하지만, VM 측은 Tier 1 제약 때문에 Ubuntu 베이스 이미지 교체가 필수이고, 권장 경로는 Humble EOL(2027-05) 전에 Jazzy(24.04 VM, MoveIt 공식 권장) 또는 Lyrical(26.04 VM, 2031년까지 지원)로 이행하는 것이다. Kilted/Rolling은 각각 짧은 지원 기간과 비안정성 때문에 프로덕션 고정 대상으로 부적합하다.

**근거**: 검증된 개별 사실들(Nav2의 Humble 지원, RoboStack 다배포판 채널, REP-2000 Tier 1 제약, MoveIt의 Jazzy 권장)로부터의 합성 결론. 단, zenoh 브리지가 서로 다른 배포판(예: mac 측 Jazzy ↔ VM 측 Humble) 간 통신을 지원하는지는 이번 검증 클레임에 포함되지 않아 별도 확인이 필요하며, 이 점이 '점진적(비동시) 업그레이드' 가능 여부를 좌우한다.

**소스**:
- https://reps.openrobotics.org/rep-2000/
- https://robostack.github.io/GettingStarted.html
- https://moveit.ai/
- https://docs.ros.org/en/humble/Related-Projects.html

## 반박된 주장 (2건 — 투명성 기록)

- (1-2) "MoveIt's scope is broader than pure motion planning: it is a package set covering motion planning, manipulation, kinematics, 3D perception, control, and navigation within ROS." — https://www.sciencedirect.com/science/article/pii/S0736584523000352
- (1-2) "MoveIt 2 supports multiple ROS 2 distributions with distinct version tracks: Rolling (MoveIt 2.13), Jazzy (2.12, LTS, recommended), Iron (2.7), Humble (2.5, LTS), Galactic (2.3), and Foxy (2.2), plus ROS 1 Noetic (MoveIt 1.1)." — https://moveit.ai/

## Caveats

(1) zenoh 브리지 관련: rosmac의 핵심 요소인 zenoh 브리지(rmw_zenoh 또는 zenoh-bridge-ros2dds)가 이기종 배포판 간(예: Humble VM ↔ Jazzy mac) 메시지 호환을 보장하는지는 검증된 클레임이 전혀 없다 — 아키텍처 평가의 가장 큰 공백. (2) 검증자 정정: 한 확정 클레임(21번)의 'Lyrical은 Ubuntu 24.04 필요' 부분은 오류이며 Lyrical Luth의 Tier 1은 Ubuntu 26.04다(결론 방향은 불변, 오히려 강화). (3) Kilted EOL은 REP-2000(2026-11)과 endoflife.date(2026-12) 간 1개월 불일치가 있다. (4) MoveIt 공식 자기서술의 'navigation' 포함은 마케팅 잔재로, 실제 베이스 내비게이션 기능을 의미하지 않는다(별도 확정 클레임에서 반박됨). (5) RoboStack의 osx-arm64 패키지 커버리지는 배포판별로 불완전(특히 Kilted)하므로 MoveIt/Nav2 등 구체 패키지의 Jazzy/Lyrical osx-arm64 빌드 존재는 마이그레이션 전 개별 확인 필요. (6) 시간 민감성: 모든 지원 상태·권장 라벨은 2026-07-10 기준이며, Lyrical Luth 출시(2026-05) 직후라 MoveIt의 Lyrical 지원 현황은 아직 유동적일 수 있다. (7) docs.ros.org 일부 페이지는 봇 차단(Anubis)으로 GitHub 원본 소스로 검증했다(내용 동일성은 확인됨).

## Open questions (후속 조사 후보)

- zenoh 브리지(rmw_zenoh / zenoh-bridge-ros2dds)가 서로 다른 ROS 2 배포판 간(예: mac 측 Jazzy ↔ VM 측 Humble) 통신을 공식 지원하는가? 이것이 가능하면 rosmac의 양측을 비동시적으로 업그레이드할 수 있다.
- RoboStack robostack-jazzy / robostack-lyrical 채널의 osx-arm64에서 MoveIt 2와 Nav2 전체 패키지 세트가 실제로 빌드·배포되어 있는가(패키지별 가용성 표 확인 필요)?
- Lima VM을 Ubuntu 22.04에서 24.04(또는 26.04)로 교체할 때의 구체적 마이그레이션 비용 — 기존 워크스페이스 재빌드, GPU/가상화 설정, provisioning 스크립트 수정 범위는?
- Nav2와 MoveIt의 Lyrical Luth(2026-05 LTS) 공식 바이너리 지원은 언제 안정화되는가 — Humble EOL(2027-05) 전에 Jazzy를 건너뛰고 Lyrical로 직행하는 것이 현실적인가?

## 소스 목록 (품질 판정 포함)

- [unreliable] https://micro.ros.org/docs/tutorials/demos/moveit2_demo/ (claims: 0)
- [primary] https://robostack.github.io/GettingStarted.html (claims: 5)
- [primary] https://github.com/RoboStack/ros-jazzy (claims: 5)
- [primary] https://docs.ros.org/en/humble/Related-Projects.html (claims: 5)
- [primary] https://github.com/moveit/moveit2 (claims: 5)
- [primary] https://prefix.dev/channels/robostack-jazzy/packages/ros-jazzy-moveit2-tutorials (claims: 5)
- [primary] https://moveit.ai/ (claims: 5)
- [primary] https://moveit.picknik.ai/humble/index.html (claims: 4)
- [primary] https://arxiv.org/pdf/2307.15236 (claims: 5)
- [primary] https://docs.ros.org/en/rolling/Related-Projects.html (claims: 5)
- [primary] https://moveit.ai/events/rosworld-2021-workshop/MoveIt%20and%20the%20rest%20of%20ROS_%20Perception,%20Control,%20and%20Simulation%20ROSWorld%20October%202021%20-%20Mobile%20Manipulation%20Workshop.pdf (claims: 5)
- [primary] https://reps.openrobotics.org/rep-2000/ (claims: 5)
- [primary] https://moveit.picknik.ai/humble/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html (claims: 5)
- [primary] https://github.com/RoboStack/ros-jazzy/issues/26 (claims: 5)
- [primary] https://github.com/RoboStack/ros-kilted (claims: 5)
- [secondary] https://endoflife.date/ros-2 (claims: 5)
- [unreliable] https://docs.ros.org/en/lyrical/Releases/Release-Lyrical-Luth.html (claims: 0)
- [primary] https://robostack.github.io/humble.html (claims: 5)
- [forum] https://discourse.openrobotics.org/t/incompatability-between-distributions/43747 (claims: 5)
- [primary] https://github.com/ros2/rmw_fastrtps/issues/797 (claims: 5)
- [primary] https://github.com/ros2/rmw_zenoh/issues/425 (claims: 4)
- [primary] https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds (claims: 5)
- [primary] https://docs.ros.org/en/humble/The-ROS2-Project/Release-Schedule.html (claims: 5)
- [primary] https://moveit.picknik.ai/humble/index.html (claims: 3)
- [primary] https://moveit.picknik.ai/humble/doc/examples/hybrid_planning/hybrid_planning_tutorial.html (claims: 5)
- [secondary] https://docs.elephantrobotics.com/docs/mycobot_280_m5_en/3-FunctionsAndApplications/6.developmentGuide/ROS/12.2-ROS2/12.2.5-Moveit2/ (claims: 5)
- [unreliable] https://docs.ros.org/en/lyrical/Releases/Release-Lyrical-Luth.html (claims: 0)
- [primary] https://moveit.picknik.ai/humble/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html (claims: 5)
- [primary] https://moveit.ai/ (claims: 5)
- [secondary] https://endoflife.date/ros-2 (claims: 5)
- [primary] https://reps.openrobotics.org/rep-2000/ (claims: 5)
- [primary] https://prefix.dev/channels/robostack-jazzy/packages/ros-jazzy-moveit2-tutorials (claims: 5)
- [forum] https://discourse.openrobotics.org/t/incompatability-between-distributions/43747 (claims: 5)
- [primary] https://robostack.github.io/GettingStarted.html (claims: 5)
- [forum] https://github.com/ros2/rmw_fastrtps/issues/797 (claims: 5)
- [primary] https://github.com/ros2/rmw_zenoh/issues/425 (claims: 4)
- [primary] https://github.com/RoboStack/ros-jazzy (claims: 5)
- [primary] https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds (claims: 5)
- [primary] https://docs.ros.org/en/humble/The-ROS2-Project/Release-Schedule.html (claims: 5)
- [primary] https://github.com/RoboStack/ros-kilted (claims: 5)
- [primary] https://www.sciencedirect.com/science/article/pii/S0736584523000352 (claims: 5)

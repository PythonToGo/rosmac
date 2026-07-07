# Phase 3 — (실험) GPU 가속 VM 백엔드

> 목표: VM 안의 Gazebo 센서 렌더링/GUI에 GPU 가속을 제공할 수 있는지 검증하고,
> 기준 충족 시 rosmac의 교체 가능한 백엔드로 채택한다.
> 성격: **실험 트랙** — 실패해도 Phase 1~2 산출물은 온전히 유효하다.
> 착수 조건: Phase 2 완료 + 2.4에서 기록한 성능 수치가 베이스라인으로 존재
> 예상 소요: 1~2주 (탐색 성격, 상한을 정해두고 초과 시 중단)

## 배경

Apple Silicon에서 Linux VM에 GPU를 노출하는 실용 스택은
**libkrun/krunkit + virtio-gpu(Venus) → Vulkan → (호스트) Metal** 계열이다
(podman machine의 libkrun 프로바이더가 실사용 사례). Gazebo(OGRE2)는
OpenGL을 쓰므로 VM 내부에서 **Zink(OpenGL→Vulkan)** 를 거쳐 Venus로 나가는
경로가 성립하는지가 관건이다. 이 체인(OGRE2→GL→Zink→Venus→Metal)의 각 고리가
검증 대상이며, 어느 고리든 끊기면 그 지점을 기록하고 중단한다.

## 판정 기준 (사전 확정 — 결과 보고 정하지 않기)

| 지표 | 베이스라인 (Phase 2.4, Lima 소프트웨어 렌더링) | 채택 기준 |
|---|---|---|
| 카메라 센서 시뮬 RTF | 실측값 B1 | ≥ 2 × B1 또는 RTF ≥ 0.9 |
| 카메라 `/image` fps | 실측값 B2 | ≥ 2 × B2 |
| 안정성 | — | 30분 연속 시뮬 크래시 0회 |
| 운영 복잡도 | — | `rosmac init`에 통합 가능한 수준의 자동화 |

## 태스크

### 3.1 스택 조사 및 최소 재현 (timebox: 3일)
1. krunkit 설치 경로 확인 (`brew install krunkit` 또는 podman machine 경유) — 버전 기록
2. ARM64 Linux 게스트 기동 + 게스트에 mesa(venus, zink) 확인:
   ```bash
   vulkaninfo --summary        # venus 디바이스가 보이는가
   glxinfo -B                  # (Zink 경유) OpenGL 벤더/버전
   ```
3. `glmark2` 실행 — 소프트웨어 렌더링(llvmpipe) 대비 점수 기록
4. **게이트**: vulkaninfo에 venus가 안 보이거나 glmark2가 llvmpipe 이하 → 조사 결과
   기록 후 Phase 3 중단 (스택 성숙도 부족 판정, 6개월 뒤 재평가 메모 남김)

### 3.2 Gazebo 벤치마크 (timebox: 3일)
1. 3.1 게스트에 Ubuntu 22.04 userland 준비가 어려우면(krunkit 이미지 제약)
   컨테이너로 우회: krunkit VM 안에서 Humble 컨테이너 실행 (구성 기록)
2. Phase 2.4와 **동일한 월드/센서 구성**으로 RTF, fps 측정 (변인 통제)
3. 판정표 채우기 → 채택/기각 결정

### 3.3 (채택 시) 백엔드 추상화
1. `lima.py`가 구현하는 인터페이스를 `VmBackend` 프로토콜로 추출:
   `provision() / start() / stop() / shell(cmd) / forward_port()`
2. `krunkit.py` 구현 + config에 `vm.backend: lima | krunkit`
3. Phase 1 E2E + Phase 2 E2E를 krunkit 백엔드로 전체 재실행 — 둘 다 통과해야 병합
4. 기본값은 여전히 lima (안정성 우선), krunkit는 opt-in으로 문서화

### 완료 기준 (AC)
- [ ] `docs/plan/phase3-results.md`: 판정표 수치, 채택/기각 결정, (기각 시) 끊긴 고리와 재평가 시점
- [ ] (채택 시) 두 백엔드 모두 E2E 통과

## 명시적 비목표
- eGPU/외부 렌더 서버, 원격 GPU 스트리밍
- RViz2 자체의 Metal 포팅 (업스트림 규모 — 본 프로젝트 범위 밖)

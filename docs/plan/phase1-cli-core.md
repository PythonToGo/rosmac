# Phase 1 — rosmac CLI 코어

> 목표: Phase 0에서 손으로 검증한 절차를 `rosmac` 명령어로 자동화한다.
> 착수 조건: Phase 0 게이트 GO
> E2E 성공 기준: 새 맥(또는 전부 삭제한 상태)에서 `rosmac init && rosmac up` 후,
> 맥 셸에서 `ros2 topic echo /chatter`로 VM talker 메시지가 수신된다.
> 예상 소요: 1~2주 (파트타임 기준)

## 태스크 의존 그래프

```
1.1 스캐폴딩 ─→ 1.2 config ─→ 1.3 Lima 템플릿 자산화 ─→ 1.4 init
                                                        ├→ 1.5 up/down/status
                                                        ├→ 1.6 doctor
                                                        └→ 1.7 shell
1.4~1.7 완료 ─→ 1.8 E2E 수용 테스트
```

---

## 1.1 리포 스캐폴딩

### 수행 절차
1. `git init` + Python 프로젝트 생성:
   ```
   pyproject.toml        # [project] name="rosmac", requires-python=">=3.11"
                         # deps: typer, rich, pyyaml, pydantic
                         # [project.scripts] rosmac = "rosmac.cli:app"
   src/rosmac/__init__.py, cli.py
   tests/unit/, tests/e2e/
   .gitignore            # .venv, __pycache__, ~/.rosmac 아님(홈 밖)
   ```
2. 개발 환경: `python -m venv .venv && pip install -e ".[dev]"` (dev: pytest, ruff, mypy)
3. `cli.py`에 typer 앱 + `rosmac version` 서브커맨드만 구현 (배선 확인용).
4. ruff/mypy 설정을 pyproject에 포함, `pytest -q` 통과하는 빈 테스트 1개.

### 완료 기준 (AC)
- [ ] `pipx install -e .` 또는 venv에서 `rosmac version` 출력
- [ ] `ruff check .`, `pytest` 클린
- [ ] 첫 커밋 `[P1.1] scaffold`

---

## 1.2 config 모듈

### 설계
- 파일 위치: `~/.rosmac/config.yaml` (없으면 기본값으로 자동 생성)
- pydantic 모델로 스키마 정의:
  ```yaml
  vm:
    name: rosmac          # lima 인스턴스 이름
    cpus: 4
    memory: 8GiB
    disk: 30GiB
  bridge:
    port: 7447
    version: "<Phase 0에서 핀한 버전>"
  ros:
    distro: humble
    domain_id: 0
    rmw: "<Phase 0 결과의 RMW>"   # fastrtps | cyclonedds
  conda:
    env_name: ros_env
    channel: robostack-humble     # Phase 0에서 확인한 현행 채널명
  foxglove:
    port: 8765
  ```
- 모든 서브커맨드는 이 config만 읽는다 (하드코딩 금지 — Phase 3 백엔드 교체 대비).

### 완료 기준 (AC)
- [ ] 최초 실행 시 기본 config 생성, 잘못된 값에 명확한 에러 (pydantic validation)
- [ ] 단위 테스트: 로드/기본값/검증 실패 3케이스

---

## 1.3 Lima 템플릿 + 프로비저닝 스크립트 자산화

### 수행 절차
1. Phase 0.2에서 **실제로 통과한** YAML/스크립트를 가져와 분리:
   - `src/rosmac/assets/lima/rosmac.yaml.j2` — cpus/memory/disk/포트를 config에서 주입
     (jinja2 대신 str.format으로 충분하면 그걸로 — 의존성 최소화)
   - `src/rosmac/assets/provision/10-ros2-humble.sh` — apt 설치
   - `src/rosmac/assets/provision/20-bridge.sh` — zenoh-bridge 바이너리 다운로드(버전 핀,
     sha256 검증), `/usr/local/bin`에 설치, systemd 유닛 등록:
     ```ini
     # /etc/systemd/system/zenoh-bridge.service
     [Service]
     Environment=ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID={domain_id}
     ExecStart=/usr/local/bin/zenoh-bridge-ros2dds -l tcp/0.0.0.0:{port}
     Restart=on-failure
     [Install]
     WantedBy=multi-user.target
     ```
     → VM 쪽 브리지는 systemd가 관리 (T9 재연결 요구를 OS에 위임)
2. `lima.py` 래퍼: `limactl start/stop/delete/list/shell`을 subprocess로 감싸고,
   JSON 출력(`limactl list --json`) 파싱해서 상태를 반환. 에러는 stderr 포함해 래핑.

### 완료 기준 (AC)
- [ ] 렌더링된 YAML로 `limactl start`가 Phase 0.2와 동일하게 무인 성공
- [ ] VM 부팅 직후 `systemctl is-active zenoh-bridge` == active
- [ ] 단위 테스트: 템플릿 렌더링 스냅샷 테스트 (subprocess는 mock)

---

## 1.4 `rosmac init`

### 동작 명세 (순서대로, 각 단계 멱등)
1. **의존성 검사**: brew, lima(버전 하한), micromamba 존재 확인.
   없으면 설치 명령을 **출력만** 하고 중단 (사용자 시스템을 임의로 바꾸지 않는다 — 단,
   `--auto` 플래그 시 brew install 실행).
2. **conda env**: `micromamba env list`에 env 없으면 생성 (Phase 0.1의 패키지 목록 + 버전 핀).
   있으면 스킵 + "이미 존재" 출력.
3. **맥용 zenoh-bridge**: `~/.rosmac/bin/zenoh-bridge-ros2dds`에 다운로드(버전 핀 + sha256).
4. **VM 프로비저닝**: 1.3 템플릿으로 `limactl start`. 이미 있으면 스킵.
5. **요약 출력**: 각 단계 ✓/스킵/실패를 rich 테이블로.

### 실패 처리
- 각 단계는 독립적으로 재시도 가능해야 함 — `rosmac init`을 다시 실행하면
  실패한 단계부터 이어서 진행되는 효과 (상태 파일이 아니라 **실제 상태 조회**로 판단).

### 완료 기준 (AC)
- [ ] 깨끗한 상태에서 init 1회 → 전 단계 성공
- [ ] 직후 init 재실행 → 전 단계 "스킵" (멱등성)
- [ ] VM만 삭제 후 init → VM 단계만 재수행
- [ ] 소요 시간 로그 (사용자 기대치 설정용)

---

## 1.5 `rosmac up / down / status`

### 동작 명세
- `up`:
  1. VM이 정지 상태면 `limactl start rosmac` (프로비저닝은 안 함 — init의 몫)
  2. VM 쪽 브리지: systemd라 자동 — `systemctl is-active` 확인만
  3. 맥 쪽 브리지 기동: `ROS_LOCALHOST_ONLY=1 ~/.rosmac/bin/zenoh-bridge-ros2dds -e tcp/127.0.0.1:{port}`
     - pidfile: `~/.rosmac/run/bridge.pid`. 이미 살아 있으면 재기동하지 않음 (R6: 이중 실행 금지)
     - 로그: `~/.rosmac/log/bridge.log` (rotate: 기동 시 이전 로그 `.1`로)
  4. 연결 스모크: 맥에서 `ros2 topic list` 실행해 VM 쪽 브리지 헬스 토픽 확인
     (없으면 경고와 함께 doctor 안내)
- `down`: 맥 브리지 종료(SIGTERM→3초→SIGKILL) → `limactl stop rosmac`
  - `--keep-vm` 플래그: 브리지만 내림
- `status`: VM 상태 / 양측 브리지 상태 / 포트 도달성 / conda env 존재를 rich 테이블로

### 완료 기준 (AC)
- [ ] up→status→down→status 사이클이 표와 일치
- [ ] up 두 번 연속 실행해도 브리지 프로세스 1개 (pidfile 검증)
- [ ] 브리지 프로세스를 kill -9 한 뒤 up → 정상 복구
- [ ] down 후 잔여 프로세스 0 (`pgrep -f zenoh-bridge` 빈 결과)

---

## 1.6 `rosmac doctor`

### 체크 목록 (각 항목: PASS/WARN/FAIL + 한 줄 처방)
| # | 검사 | 방법 | FAIL 처방 메시지 |
|---|---|---|---|
| C1 | lima 설치/버전 | `limactl --version` | brew install lima |
| C2 | VM 존재/상태 | `limactl list --json` | rosmac init / rosmac up |
| C3 | conda env 존재 | `micromamba env list` | rosmac init |
| C4 | 필수 env vars | 현재 셸의 ROS_LOCALHOST_ONLY, ROS_DOMAIN_ID, RMW | rosmac shell 사용 안내 |
| C5 | 포트 7447 도달성 | TCP connect 시도 | VM/포트포워딩 점검 |
| C6 | 맥 브리지 프로세스 | pidfile + 프로세스 생존 | rosmac up |
| C7 | VM 브리지 서비스 | `limactl shell ... systemctl is-active` | 로그 경로 안내 |
| C8 | **왕복 자가 테스트** | 고유 토픽(`/rosmac/doctor/<uuid>`)을 VM에서 pub, 맥에서 echo 5초 대기 | 브리지 로그 확인 안내 |
| C9 | RoboStack 지문 검사 | 알려진 깨진 dylib 목록을 `otool -L`로 검사 (Phase 0.1 핀 목록 기반) | 핀 설치 명령 출력 |
| C10 | SIP 상태 | `csrutil status` — **정보성** (우리는 SIP 끄지 않음이 정상) | — |
| C11 | 디스크 여유 | VM diff 이미지 경로 확인 | — |

### 구현 노트
- 각 체크는 `Check` 프로토콜(name, run() -> Result) 구현체로 — 목록에 추가만 하면 확장.
- `--json` 출력 모드 (Phase 2에서 sim 프리셋이 사전 점검으로 재사용).

### 완료 기준 (AC)
- [ ] 정상 상태에서 전부 PASS
- [ ] 고장 시나리오 3종 재현 테스트: VM 정지 / 브리지 kill / env 삭제 → 각각 정확한 항목만 FAIL + 처방 출력

---

## 1.7 `rosmac shell`

### 동작 명세
- 새 서브셸(사용자 $SHELL)을 열고 다음을 주입:
  micromamba env 활성화 + `ROS_LOCALHOST_ONLY=1` + `ROS_DOMAIN_ID` + RMW + PS1 프리픽스 `(rosmac)`
- `rosmac shell --vm`: `limactl shell rosmac`으로 진입 (bashrc에 ROS 소싱은 프로비저닝에서 완료)
- 구현: 임시 rc 파일 생성 후 `zsh --rcs` 방식 (환경이 사용자 rc와 충돌하지 않게 문서화)

### 완료 기준 (AC)
- [ ] shell 진입 후 `ros2 topic list`가 즉시 동작 (env 수동 설정 0회)
- [ ] `--vm` 진입 후 동일

---

## 1.8 E2E 수용 테스트

### 시나리오 (스크립트화: `tests/e2e/test_smoke.sh`)
```
1. limactl delete -f rosmac; micromamba env remove -n ros_env  # 초기화
2. rosmac init            → exit 0
3. rosmac up              → exit 0
4. limactl shell rosmac -- ros2 run demo_nodes_cpp talker &   # VM에서 발행
5. rosmac shell -c 'timeout 10 ros2 topic echo /chatter --once'  → 메시지 수신
6. rosmac doctor          → 전부 PASS
7. rosmac down            → 잔여 프로세스 0
```

### 완료 기준 (AC)
- [ ] 위 스크립트가 처음부터 끝까지 무인 통과
- [ ] 총 소요 시간 기록 → README의 "설치 소요" 문구 근거
- [ ] 결과를 `docs/plan/phase1-results.md`에 기록, Phase 2 착수 게이트

### Phase 1 범위에서 의도적으로 제외한 것 (스코프 크리프 방지)
- GUI 앱 번들, brew tap 배포 (동작이 먼저)
- 멀티 VM / 멀티 배포판 지원
- Windows/Linux 호스트 지원

---

## 부록 A — pyproject.toml 전문 (1.1에서 이대로 시작)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "rosmac"
version = "0.1.0"
description = "One-command ROS2 Humble dev environment for Apple Silicon Macs"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "rich>=13",
    "pyyaml>=6",
    "pydantic>=2",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.4", "mypy>=1.10", "types-PyYAML"]

[project.scripts]
rosmac = "rosmac.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/rosmac"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.pytest.ini_options]
testpaths = ["tests/unit"]   # e2e는 명시 실행: pytest tests/e2e -m e2e
markers = ["e2e: requires real VM"]

[tool.mypy]
python_version = "3.11"
packages = ["rosmac"]
mypy_path = "src"
```

## 부록 B — 모듈 스켈레톤 (함수 시그니처 = 계약. 이름/타입을 바꾸지 말 것)

**`src/rosmac/cli.py`**
```python
import typer

app = typer.Typer(no_args_is_help=True,
                  help="ROS2 Humble dev environment for Apple Silicon Macs")

@app.command()
def version() -> None: ...

@app.command()
def init(auto: bool = typer.Option(False, "--auto",
         help="brew 의존성을 확인 후 자동 설치")) -> None: ...

@app.command()
def up(viz: bool = typer.Option(False, "--viz")) -> None: ...

@app.command()
def down(keep_vm: bool = typer.Option(False, "--keep-vm")) -> None: ...

@app.command()
def status() -> None: ...

@app.command()
def doctor(json_out: bool = typer.Option(False, "--json")) -> None: ...

@app.command()
def shell(vm: bool = typer.Option(False, "--vm"),
          command: str | None = typer.Option(None, "-c")) -> None: ...
# sim 서브앱은 Phase 2에서 추가: app.add_typer(sim_app, name="sim")
```

**`src/rosmac/config.py`**
```python
from pathlib import Path
from pydantic import BaseModel

CONFIG_PATH = Path.home() / ".rosmac" / "config.yaml"

class VmConfig(BaseModel):
    name: str = "rosmac"
    cpus: int = 4
    memory: str = "8GiB"
    disk: str = "30GiB"

class BridgeConfig(BaseModel):
    port: int = 7447
    version: str      # 기본값 없음 — Phase 0 결과에서 핀한 값을 코드에 박는다
    sha256_darwin: str
    sha256_linux: str

class RosConfig(BaseModel):
    distro: str = "humble"
    domain_id: int = 0
    rmw: str          # Phase 0 결과값

class Config(BaseModel):
    vm: VmConfig = VmConfig()
    bridge: BridgeConfig
    ros: RosConfig
    conda_env: str = "ros_env"
    conda_channel: str    # Phase 0 결과값
    foxglove_port: int = 8765

def load() -> Config: ...      # 없으면 기본 생성 후 로드, 검증 실패 시 명확한 에러
```

**`src/rosmac/lima.py`**
```python
from enum import Enum

class VmState(Enum):
    ABSENT = "absent"; STOPPED = "Stopped"; RUNNING = "Running"

def state(name: str) -> VmState: ...              # limactl list --json 파싱
def start(name: str, template_path: str) -> None: ...   # 실패 시 stderr 포함 RuntimeError
def stop(name: str) -> None: ...
def delete(name: str) -> None: ...
def shell(name: str, cmd: str, timeout: int = 60) -> str: ...  # stdout 반환
```

**`src/rosmac/doctor.py`**
```python
from typing import Literal, NamedTuple, Protocol
from rosmac.config import Config

class CheckResult(NamedTuple):
    name: str
    status: Literal["PASS", "WARN", "FAIL"]
    detail: str
    remedy: str | None = None    # FAIL일 때 사용자에게 보여줄 한 줄 처방

class Check(Protocol):
    name: str
    def run(self, cfg: Config) -> CheckResult: ...

CHECKS: list[Check] = []   # C1..C11을 순서대로 등록. 새 체크는 여기 추가만 하면 됨

def run_all(cfg: Config) -> list[CheckResult]: ...
```

**`src/rosmac/bridge.py`**
```python
# 맥 쪽 브리지 프로세스 관리. pidfile: ~/.rosmac/run/bridge.pid
def is_running() -> bool: ...        # pidfile 존재 + 해당 pid의 cmdline에 zenoh-bridge 확인
def start(cfg) -> None: ...          # is_running()이면 no-op (R6). 로그 rotate 후 Popen
def stop() -> None: ...              # SIGTERM → 3초 대기 → SIGKILL, pidfile 정리
```

## 부록 C — 구현 세부 결정 (약한 모델이 헤맬 지점 미리 결정)

1. **subprocess 원칙**: `subprocess.run([...], capture_output=True, text=True, timeout=N)`.
   `shell=True` 금지 (경로에 공백 있는 맥 사용자명 이슈 + 인젝션).
   limactl shell 경유 명령만 예외적으로 `bash -lc '<cmd>'` 래핑.
2. **에러 표면화**: 래퍼는 실패 시 `RuntimeError(f"{cmd} failed: {stderr}")` —
   에러를 삼키고 False만 반환하지 말 것 (doctor가 detail에 stderr를 실어야 함).
3. **템플릿 렌더링**: jinja2 쓰지 않는다. `string.Template.substitute()` 사용
   (YAML 안의 `${...}`와 충돌 없게 구분자 확인). 렌더 결과는 `~/.rosmac/lima/rosmac.yaml`에
   쓰고 그 경로로 limactl 호출.
4. **다운로드**: `urllib.request` + sha256 검증 (외부 dep 추가 금지).
   검증 실패 시 파일 삭제 후 에러.
5. **`rosmac shell` 구현**: 임시 zshrc를 만들어
   `ZDOTDIR=<tmpdir> zsh -i` 로 진입. 임시 zshrc 내용:
   `source ~/.zshrc 2>/dev/null` → micromamba activate → export ROS_* → PS1 프리픽스.
   `-c` 옵션이면 인터랙티브 대신 `zsh -c` (E2E 스크립트용).
6. **출력 스타일**: rich Console 하나를 `cli.py`에서 생성해 주입. 단계 출력은
   `console.status()` 스피너 + 완료 시 ✓/✗ 라인. `--json` 모드에서는 rich 출력 억제.
7. **테스트에서 subprocess mock**: `lima.py` 등은 module-level 함수이므로
   `monkeypatch.setattr(lima, "_run", fake)` 패턴 — `_run(cmd) -> CompletedProcess`
   내부 헬퍼 하나로 모든 외부 호출을 몰아넣는다.

## 부록 D — E2E 판정 스니펫 (1.8)

`tests/e2e/test_smoke.sh`의 핵심 판정부 (그대로 사용 가능):
```bash
set -euo pipefail
# 5단계: 메시지 수신 판정
OUT=$(rosmac shell -c 'timeout 10 ros2 topic echo /chatter --once' || true)
echo "$OUT" | grep -q "Hello World" \
  && echo "E2E-5 PASS" || { echo "E2E-5 FAIL: $OUT"; exit 1; }
# 7단계: 잔여 프로세스 판정
rosmac down
sleep 2
pgrep -f zenoh-bridge-ros2dds && { echo "E2E-7 FAIL: bridge alive"; exit 1; } \
  || echo "E2E-7 PASS"
```

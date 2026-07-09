# 실로봇 연결

*(English: [robot-setup.md](robot-setup.md))*

rosmac은 로봇과 TCP 링크 하나로 통신한다: 로봇에 `zenoh-bridge-ros2dds`
리스너를 하나 띄우고, 맥 브리지가 거기로 접속한다. 로봇에 설치되는 것은 이
바이너리 하나뿐 — 이 문서는 복붙용 가이드이고, `rosmac`이 로봇에서 뭔가를
실행하는 일은 없다.

```
Mac (RoboStack) ── zenoh 브리지 ──┬── tcp ──> Lima VM (Ubuntu, 심/빌드)
                                  └── tcp ──> robot :7447  ← 이 가이드
```

접속은 맥이 시작한다(스타 토폴로지) — 로봇이 맥으로 들어올 필요가 없다.
VM과 로봇도 서로의 토픽을 볼 수 있다(맥 브리지를 통한 전이 라우팅).

## 1. 사전 조건 (먼저 읽을 것)

- **ROS 2 Humble이 설치된 Ubuntu 로봇.** v1은 Humble만 지원 — 배포판 혼합은
  미검증 영역.
- **로봇 노드는 CycloneDDS RMW 필수.** 기본 Fast DDS로는 토픽은 되는 것처럼
  보이지만 **브리지 경유 서비스 호출이 전부 타임아웃**된다(실측). 로봇에서:

  ```bash
  sudo apt install ros-humble-rmw-cyclonedds-cpp
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp   # ~/.bashrc / launch 환경에
  ```

- **`ROS_DOMAIN_ID` 전부 일치**: 로봇 노드, 아래 systemd 유닛, 맥의
  `~/.rosmac/config.yaml`의 `ros.domain_id`. 불일치는 *조용히* 실패한다 —
  링크는 멀쩡해 보이는데 토픽이 안 흐른다.
- **`ROS_LOCALHOST_ONLY`도 로봇 노드와 일치 필수.** 브리지는 로컬 DDS로
  노드를 발견한다 — 노드는 `ROS_LOCALHOST_ONLY=1`인데 브리지는 아니면(또는
  반대) 서로를 영영 못 본다. 역시 *무증상* 실패다(실측). 아래 유닛은 미설정
  (일반적인 로봇 구성)이며, localhost-only 로봇용 복붙 처방은 2.1절에.
- **7447/tcp 개방** — 맥에서 로봇으로 (ufw 사용 시 `sudo ufw allow 7447/tcp`).
- **신뢰 LAN 전용.** 링크는 인증 없는 평문 TCP다. 7447 포트를 로컬 네트워크
  밖으로 노출하지 말 것.

## 2. 로봇 쪽 설치 (복붙)

로봇에서 실행. 핀된 브리지 바이너리를 내려받고(sha256 검증,
aarch64/x86_64 자동 감지) systemd 서비스로 등록한다.

```bash
#!/bin/bash
set -euo pipefail

VER="1.9.0"
case "$(uname -m)" in
  aarch64) ARCH="aarch64"; SHA="e3eb1fd4459e4b877653419b1c25eaf92418d70fe53ee767eca005f1a19443dc" ;;
  x86_64)  ARCH="x86_64";  SHA="91aa0d569fffd57e7ebb1a591b97789891c543b1ff0a1658413ce6cbbba34a9e" ;;
  *) echo "unsupported arch: $(uname -m)"; exit 1 ;;
esac
ZIP="/tmp/zenoh-bridge.zip"
curl -sSL -o "$ZIP" \
  "https://github.com/eclipse-zenoh/zenoh-plugin-ros2dds/releases/download/${VER}/zenoh-plugin-ros2dds-${VER}-${ARCH}-unknown-linux-gnu-standalone.zip"
echo "${SHA}  ${ZIP}" | sha256sum -c -
sudo unzip -o "$ZIP" zenoh-bridge-ros2dds -d /usr/local/bin
sudo chmod +x /usr/local/bin/zenoh-bridge-ros2dds
rm -f "$ZIP"

sudo tee /etc/systemd/system/zenoh-bridge-ros2dds.service > /dev/null <<'UNIT'
[Unit]
Description=zenoh-bridge-ros2dds (robot side, for rosmac)
After=network-online.target

[Service]
# ROS_DOMAIN_ID는 로봇 노드·맥의 ros.domain_id와 반드시 일치해야 한다.
Environment=ROS_DOMAIN_ID=0 ROS_DISTRO=humble
ExecStart=/usr/local/bin/zenoh-bridge-ros2dds -l tcp/0.0.0.0:7447
Restart=on-failure
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now zenoh-bridge-ros2dds.service
```

로봇에서 확인:

```bash
systemctl is-active zenoh-bridge-ros2dds   # → active
ss -tln | grep 7447                        # → LISTEN 0.0.0.0:7447
journalctl -u zenoh-bridge-ros2dds --no-pager | grep Discovered   # → 내 노드들
```

마지막 명령에 내 노드가 하나도 안 보이면 브리지가 DDS에서 노드를 못 보는
상태다 — `ROS_DOMAIN_ID`와 `ROS_LOCALHOST_ONLY`를 확인 (둘 다 무증상 실패).

### 2.1 로봇 노드가 `ROS_LOCALHOST_ONLY=1`로 도는 경우

브리지도 맞춰야 한다 — 아니면 영영 발견 못 한다. 복붙:

```bash
sudo mkdir -p /etc/systemd/system/zenoh-bridge-ros2dds.service.d
printf '[Service]\nEnvironment=ROS_LOCALHOST_ONLY=1\n' | \
  sudo tee /etc/systemd/system/zenoh-bridge-ros2dds.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart zenoh-bridge-ros2dds
```

재시작 후 맥이 자동 재접속하므로 맥 쪽 조작은 불필요.

## 3. 맥에서 연결

`~/.rosmac/config.yaml`에 로봇 IP(또는 호스트명)를 추가:

```yaml
robot:
  host: 192.168.0.42   # 로봇 주소
  port: 7447
```

그다음:

```bash
rosmac up
# ✓ robot endpoint reachable (tcp/192.168.0.42:7447)
```

config 수정 전에 맥 브리지가 이미 떠 있었다면 `up`이 드리프트 경고를 낸다 —
안내대로:

```bash
rosmac down --keep-vm && rosmac up
```

링크 확인과 로봇 토픽 수신:

```bash
rosmac status      # Robot (tcp/192.168.0.42:7447) │ reachable
rosmac ps          # ── Robot link ── 섹션: reachable ✓  in bridge args ✓
rosmac shell
ros2 topic list    # VM 토픽 옆에 로봇 토픽이 보인다
ros2 topic echo /your_robot_topic --once
```

연결 해제는 `host: null`(또는 `robot:` 블록 삭제) 후 같은 방식으로 브리지
재시작.

## 4. 운영 노트

- **로봇이 꺼져 있어도 OK.** 로봇이 unreachable이면 `rosmac up`은 경고만
  내고 성공(exit 0)한다. 로봇 리스너가 나타나는 순간 맥 브리지가 자동
  접속하므로, 로봇 재부팅·브리지 재시작에 맥 쪽 조작은 불필요.
- **서비스는 SIGTERM으로 깨끗하게 재시작, `kill -9` 금지.** 로봇 쪽 서비스
  서버를 비정상 종료하면 브리지에 이름 기반의 낡은 라우트가 남아, 대체
  서버가 재선언할 때까지 호출을 막을 수 있다(실측).
  `sudo systemctl restart zenoh-bridge-ros2dds`가 올바른 방법.
- **`robot.allow` / `robot.deny` 필터는 맥 브리지 전역** — 로봇 링크만이
  아니라 맥↔VM 경로도 함께 필터링된다.
- **브리지 버전**: 이 가이드는 1.9.0 핀. 로봇의 1.8.x도 맥의 1.9와 상호운용
  된다(토픽·서비스 실측)만, 가급적 마이너 버전을 맞출 것.
- **대역/지연 참고치** (루프백 대리 로봇 기준, WiFi 실측은 추후): 10Hz에서
  10 MB/s 무손실, 서비스 RTT < 1 ms. 카메라/포인트클라우드급 토픽은 WiFi가
  병목이 된다 — 필요하면 `robot.deny`로 무거운 토픽을 링크에서 제외.

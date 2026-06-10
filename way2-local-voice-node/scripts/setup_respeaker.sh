#!/bin/bash
# ============================================================
# 树莓派 + ReSpeaker 4-Mic 语音节点一键配置脚本
# ============================================================
# 适用环境：Raspberry Pi OS (Bookworm, 64-bit)
# 适用硬件：树莓派 4B / 5 + ReSpeaker 4-Mic Array
#
# 用法：
#   chmod +x setup_respeaker.sh
#   ./setup_respeaker.sh
#
# 这个脚本会做以下事情：
#   1. 安装系统依赖
#   2. 安装 ReSpeaker 音频驱动
#   3. 安装 Docker（可选，用于跑 Wyoming 服务）
#   4. 配置 Wyoming 语音服务（唤醒词 + ASR + TTS）
#   5. 配置服务开机自启动
# ============================================================

set -e

# ---- 颜色输出 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERR]${NC} $1"; }

# ---- 检查运行环境 ----
if [ "$EUID" -ne 0 ]; then
  log_err "请以 root 身份运行：sudo ./setup_respeaker.sh"
  exit 1
fi

echo ""
echo "============================================"
echo "  树莓派语音节点配置工具 v1.0"
echo "  ReSpeaker 4-Mic Array + Wyoming + Claude"
echo "============================================"
echo ""

# ============================================================
# 第 1 步：系统更新 + 依赖安装
# ============================================================
log_info "第 1 步：更新系统并安装依赖..."

apt update
apt upgrade -y
apt install -y \
  git python3-pip python3-venv python3-dev \
  portaudio19-dev libatlas-base-dev \
  alsa-utils pulseaudio \
  cmake build-essential \
  docker.io docker-compose-v2 \
  network-manager

log_ok "系统依赖安装完成"

# ============================================================
# 第 2 步：安装 ReSpeaker 驱动
# ============================================================
log_info "第 2 步：安装 ReSpeaker 4-Mic Array 驱动..."

cd /tmp
if [ -d "seeed-voicecard" ]; then
  rm -rf seeed-voicecard
fi

git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard

# 检测内核版本，选择安装方式
KERNEL_VER=$(uname -r | cut -d. -f1-2)
log_info "内核版本: $KERNEL_VER"

# Bookworm 内核较新，用 dkms 方式安装
if command -v dkms &> /dev/null; then
  ./install.sh 2>&1 || log_warn "驱动安装可能有非致命错误"
else
  apt install -y dkms
  ./install.sh 2>&1 || log_warn "驱动安装可能有非致命错误"
fi

log_ok "ReSpeaker 驱动安装完成"
log_info "需重启后生效，后续步骤会在重启后继续..."
log_info "请先运行：sudo reboot"
echo ""

# ============================================================
# 第 3 步：配置声卡（重启后执行第二部分）
# ============================================================
# 这个脚本是两段式设计。重启后，运行下面的第二部分：
#   ./setup_respeaker.sh --part2

if [ "$1" != "--part2" ]; then
  # 写入第二部分作为可执行脚本
  cat > /home/pi/setup_part2.sh << 'PART2EOF'
#!/bin/bash
# ---- 第二部分：重启后运行 ----

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# 检查声卡
log_info "检查 ReSpeaker 声卡..."
if aplay -l | grep -q "seeed"; then
  log_ok "ReSpeaker 声卡已识别"
else
  log_warn "未检测到 seeed 声卡，尝试手动加载模块..."
  modprobe seeed-voicecard || true
  # 再检查一次
  if aplay -l | grep -q "seeed\|card"; then
    log_ok "声卡可用"
  else
    log_err "声卡识别失败，请检查硬件连接"
    log_info "可用声卡列表："
    aplay -l
  fi
fi

# 测试录音
log_info "测试录音（3 秒）..."
arecord -d 3 -f S16_LE -r 16000 /tmp/test.wav || log_warn "录音测试失败，检查麦克风"
if [ -f /tmp/test.wav ]; then
  log_ok "录音测试完成"
  rm /tmp/test.wav
fi

# ============================================================
# 第 4 步：安装 Wyoming 语音服务（Docker 方式）
# ============================================================
log_info "第 4 步：配置 Wyoming 语音服务..."

mkdir -p /opt/wyoming

# ---- 4a. Wyoming 唤醒词服务 (Porcupine) ----
log_info "  -> 配置唤醒词服务..."
cat > /opt/wyoming/docker-compose.yml << 'DOCKERCOMPOSE'
version: '3.8'

services:
  # === 唤醒词检测 ===
  wyoming-porcupine:
    image: rhasspy/wyoming-porcupine:latest
    container_name: wyoming-porcupine
    restart: unless-stopped
    ports:
      - "10400:10400"
    command: >
      --uri tcp://0.0.0.0:10400
      --keyword hey_claude
      --sensitivity 0.5
      --threshold 0.5
      --trigger-level 1
    devices:
      - /dev/snd:/dev/snd
    volumes:
      - /etc/asound.conf:/etc/asound.conf:ro

  # === 语音转文字（ASR） ===
  wyoming-whisper:
    image: rhasspy/wyoming-faster-whisper:latest
    container_name: wyoming-whisper
    restart: unless-stopped
    ports:
      - "10300:10300"
    command: >
      --uri tcp://0.0.0.0:10300
      --model large-v3
      --language zh
      --device auto
      --initial-prompt "以下是家居控制场景的语音指令。"
    volumes:
      - whisper-data:/data

  # === 文字转语音（TTS） ===
  wyoming-piper:
    image: rhasspy/wyoming-piper:latest
    container_name: wyoming-piper
    restart: unless-stopped
    ports:
      - "10200:10200"
    command: >
      --uri tcp://0.0.0.0:10200
      --voice zh_CN-xiaoxiao-low
    volumes:
      - piper-data:/data

volumes:
  whisper-data:
  piper-data:
DOCKERCOMPOSE

# 拉取镜像
log_info "  -> 拉取 Wyoming 服务镜像..."
cd /opt/wyoming
docker compose pull

# ============================================================
# 第 5 步：配置开机自启
# ============================================================
log_info "第 5 步：配置开机自启动..."

# systemd 服务：启动 Wyoming 容器
cat > /etc/systemd/system/wyoming-voice.service << 'SYSTEMD'
[Unit]
Description=Wyoming Voice Services (Porcupine + Whisper + Piper)
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/wyoming
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
StandardOutput=journal
User=root

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable wyoming-voice.service
systemctl start wyoming-voice.service

log_ok "Wyoming 服务已启动并设为开机自启"

# ============================================================
# 第 6 步：配置 HA 连接信息
# ============================================================
log_info "第 6 步：写入 HA 连接信息..."

cat > /home/pi/ha_voice_config.txt << 'HACONFIG'
# ============================================
# 树莓派语音节点 — HA 端配置
# ============================================
#
# 在 HA 中配置 Assist Pipeline：
#
# 语音转文字：选择 "Wyoming Whisper"
#   - 服务器：树莓派的 IP 地址
#   - 端口：10300
#
# 文字转语音：选择 "Wyoming Piper"
#   - 服务器：树莓派的 IP 地址
#   - 端口：10200
#
# 唤醒词：选择 "Wyoming Porcupine"
#   - 服务器：树莓派的 IP 地址
#   - 端口：10400
#   - 唤醒词：hey_claude
#
# 对话代理：选择 "Claude Smart Home Assistant"
#   （运行在 HA 主服务器上）
# ============================================
HACONFIG

log_ok "配置信息已写入 /home/pi/ha_voice_config.txt"

echo ""
echo "============================================"
echo "  树莓派语音节点配置完成！"
echo "============================================"
echo ""
echo "下一步："
echo "  1. 获取树莓派 IP 地址：hostname -I"
echo "  2. 在 HA 中配置 Assist Pipeline："
echo "     - 唤醒词服务：   树莓派IP:10400  (hey_claude)"
echo "     - 语音转文字：   树莓派IP:10300  (Whisper)"
echo "     - 文字转语音：   树莓派IP:10200  (Piper)"
echo "     - 对话代理：     Claude Smart Home Assistant"
echo ""
echo "  3. 测试：说 \"Hey Claude，打开客厅灯\""
echo ""

PART2EOF

  chmod +x /home/pi/setup_part2.sh
  chown pi:pi /home/pi/setup_part2.sh

  echo ""
  echo "============================================"
  echo "  第一部分完成！"
  echo "============================================"
  echo ""
  echo "即将重启系统以加载音频驱动..."
  echo "重启后请登录并运行："
  echo "  sudo ./setup_part2.sh"
  echo ""
  echo "将在 5 秒后重启（按 Ctrl+C 取消）..."
  sleep 5
  reboot
fi

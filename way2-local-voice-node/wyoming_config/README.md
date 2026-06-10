# Wyoming 语音服务配置说明

## 架构

```
树莓派 + ReSpeaker 4-Mic
         │
         ├─ Porcupine（唤醒词: "Hey Claude"）
         │       │
         │       ▼  检测到唤醒词后
         ├─ Whisper（语音转文字）
         │       │
         │       ▼  文字发往 HA
         ├─ HA Assist Pipeline
         │       │
         │       ▼  Claude 处理
         ├─ Piper TTS（文字转语音）
         │       │
         │       ▼  播放回答
         └─ 3.5mm 音箱
```

## 端口分配

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| Porcupine 唤醒词 | 10400 | TCP (Wyoming) | 检测 "Hey Claude" |
| Faster Whisper ASR | 10300 | TCP (Wyoming) | 中文语音转文字 |
| Piper TTS | 10200 | TCP (Wyoming) | 中文语音合成 |

## 配置文件

### 如果使用 Docker（推荐）

参考 `docker-compose.yml` 文件内容。一键启动：

```bash
cd /opt/wyoming
docker compose up -d
```

### 如果直接运行（不依赖 Docker）

也可以直接用 Python 运行 Wyoming 服务：

```bash
# 安装 wyoming 库
pip install wyoming

# 运行唤醒词服务
python3 -m wyoming.porcupine \
  --uri tcp://0.0.0.0:10400 \
  --keyword hey_claude

# 运行 ASR 服务
python3 -m wyoming.faster_whisper \
  --uri tcp://0.0.0.0:10300 \
  --model large-v3 \
  --language zh

# 运行 TTS 服务
python3 -m wyoming.piper \
  --uri tcp://0.0.0.0:10200 \
  --voice zh_CN-xiaoxiao-low
```

## HA 端配置

在 HA 的 Assist Pipeline 中创建新管道：

1. **语音转文字（STT）** → Wyoming
   - 服务器：树莓派的 IP
   - 端口：10300

2. **文字转语音（TTS）** → Wyoming
   - 服务器：树莓派的 IP
   - 端口：10200

3. **对话代理** → Claude Smart Home Assistant

4. **唤醒词检测** → Wyoming
   - 服务器：树莓派的 IP
   - 端口：10400
   - 唤醒词：hey_claude

## 自定义唤醒词

默认唤醒词是 `hey_claude`。如果要改成其他词：

### 方法一：用 Porcupine 内置词
Porcupine 支持以下内置英语唤醒词：
- "hey_claude"（默认）
- "alexa"、"americano"、"blueberry"、"bumblebee" 等

改命令参数：
```bash
--keyword blueberry
```

### 方法二：制作自定义唤醒词（中文）
1. 去 [Picovoice Console](https://console.picovoice.ai/) 注册
2. 选 Porcupine → 创建自定义唤醒词
3. 录制 3 遍你想用的词（如"小克小克"）
4. 下载 `.ppn` 文件放到树莓派上
5. 运行：
```bash
--keyword /path/to/custom.ppn --keyword_path /path/to/custom.ppn
```

## 性能参考

| 树莓派型号 | Whisper 模型 | 识别延迟 | 建议 |
|-----------|-------------|---------|------|
| Pi 4 (4GB) | tiny / base | 1-3s | 可接受，模型小 |
| Pi 4 (8GB) | small / medium | 2-5s | 推荐 medium |
| Pi 5 (8GB) | large-v3 | 1-3s | 最佳效果 |
| Pi 5 + Coral TPU | large-v3 | <1s | 极速 |

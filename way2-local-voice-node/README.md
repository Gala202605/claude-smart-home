# 方式二：树莓派 + ReSpeaker 纯本地语音节点

**独立硬件方案**——树莓派 + 麦克风阵列做成一个专属的 Claude 语音终端，不依赖任何第三方音箱。

## 效果演示

```
你对着设备说：   "Hey Claude，客厅灯调暗到 30%"
树莓派听到唤醒词 → 唤醒 → 录音
↓
Whisper 转文字 → 发给 HA 上的 Claude
↓
Claude 理解并执行 → 灯调暗
↓
Piper TTS 播报：   "客厅灯已调暗到 30%"
```

## 你需要什么

| 项目 | 预估价格 | 说明 |
|------|---------|------|
| 🖥️ 树莓派 5 (8GB) | ¥350-400 | 推荐 8GB 跑 Whisper large-v3 |
| 🎙️ ReSpeaker 4-Mic Array | ¥150-200 | 4 麦克风阵列，远场拾音 |
| 🔈 3.5mm 有源音箱 | ¥50-100 | 或带音频输出的 HDMI 显示器 |
| 💾 MicroSD 卡 64GB | ¥50-80 | A2 速度等级，推荐 Samsung/闪迪 |
| 🔌 电源 5V/5A | ¥30-50 | 树莓派 5 官方电源 |
| 🏠 外壳（可选） | ¥0-50 | 3D 打印 / 亚克力 / 纸盒 DIY |
| **合计** | **¥630-880** | |

> 如果已有树莓派 4B，也能用（Whisper 建议用 medium 模型，延迟 2-5 秒）
> 如果预算紧张，可以先不买 3D 打印外壳，裸板跑起来再说

## 整体架构

```
┌── 树莓派 ───────────────────────────────────┐
│                                              │
│  [ReSpeaker 4-Mic] ← 远场拾音               │
│       │                                      │
│       ▼                                      │
│  [Porcupine 唤醒词检测] ─── "Hey Claude"     │
│       │                                      │
│       ▼                                      │
│  [Whisper 语音转文字] ─── 用户指令 → 文字     │
│       │                                      │
│       └─────────── TCP ───────────→  HA 服务器│
│                                              │
│       ←─────────── TCP ──────────── Claude 回复│
│       │                                      │
│       ▼                                      │
│  [Piper 文字转语音] ─── 播报回答              │
│       │                                      │
│       ▼                                      │
│  [3.5mm 音箱] ← 声音输出                     │
│                                              │
└──────────────────────────────────────────────┘
```

## 安装步骤

### 第一步：刷系统 + 连接硬件

1. 下载 [Raspberry Pi OS Lite (64-bit)](https://www.raspberrypi.com/software/)
2. 用 Raspberry Pi Imager 写入 SD 卡
   - 开启 SSH、WiFi 配置
   - 用户名：`pi`
3. 把 ReSpeaker 4-Mic 插到树莓派 GPIO 排针上（对准引脚）
4. 插音箱到 3.5mm 音频口
5. 插电开机，SSH 连接

### 第二步：运行配置脚本

```bash
# 上传脚本到树莓派
scp scripts/setup_respeaker.sh pi@树莓派IP:/home/pi/

# SSH 登录后执行
ssh pi@树莓派IP
sudo chmod +x setup_respeaker.sh
sudo ./setup_respeaker.sh
```

脚本会自动：
1. 安装系统依赖
2. 安装 ReSpeaker 声卡驱动
3. 安装 Docker
4. 拉取 Wyoming 语音服务镜像
5. **重启**树莓派

重启后继续第二段：

```bash
sudo ./setup_part2.sh
```

### 第三步：在 HA 中添加语音服务

HA → 设置 → 语音助手 → Assist Pipeline → 创建新管道：

1. **唤醒词** → Wyoming Porcupine
   - 服务器：树莓派 IP
   - 端口：10400

2. **语音转文字** → Wyoming Whisper
   - 服务器：树莓派 IP
   - 端口：10300

3. **文字转语音** → Wyoming Piper
   - 服务器：树莓派 IP
   - 端口：10200

4. **对话代理** → Claude Smart Home Assistant

### 第四步：测试

```bash
# 在树莓派上测试音频
# 录音测试
arecord -d 5 -f S16_LE -r 16000 test.wav

# 播放测试
aplay test.wav

# 查看 Wyoming 服务是否在运行
docker ps
```

然后对着 ReSpeaker 说 **"Hey Claude，现在几点了"**

## 唤醒词说明

| 关键词 | 说明 |
|--------|------|
| `hey_claude` | 默认，英文发音（嘿-克劳德） |
| 自定义唤醒词 | 在 Picovoice Console 制作中文唤醒词 |

详细说明见 [wyoming_config/README.md](./wyoming_config/README.md)

## 外壳制作

参考 [3d_print_case/case.stl](./3d_print_case/case.stl) 的说明文件。

## 与方式一对比

| 对比项 | 方式一（小爱） | 方式二（树莓派） |
|--------|--------------|----------------|
| 额外成本 | ¥0 | ¥600-900 |
| 拾音距离 | 远（小爱 mic 好） | 较远（4 mic 阵列） |
| 唤醒词 | "小爱同学" | "Hey Claude"（可定制） |
| 依赖 | 米家云服务 | 无（纯本地+HA） |
| 延迟 | 取决于 Claude API + HA | 取决于 Claude API + 本地处理 |
| 外观 | 成品音箱 | DIY 外壳 |
| 打造时间 | 15 分钟 | 1-2 天（等快递） |

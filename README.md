<p align="center">
  <h1 align="center">🏠 Claude Smart Home</h1>
  <p align="center">把 Claude 接入你的智能家居，让 AI 真正理解你</p>
  <p align="center">
    <strong>不再忍受"小爱没学会这个技能"</strong>
  </p>
  <p align="center">
    <a href="#-快速开始">快速开始</a> ·
    <a href="#-两种方式对比">方式对比</a> ·
    <a href="#-项目结构">项目结构</a> ·
    <a href="#-视频教程">视频教程</a>
  </p>
</p>

---

## 🤔 为什么做这个

小爱音箱听不懂复杂指令？说"太热了"它回"空调已设为26度"（但它并没调）？
想要一个真正能理解自然语言的智能家居——你随便说，它能听懂，能执行，还能推理。

这个项目用 **Claude + Home Assistant** 接管智能家居的语义理解层，让你家所有设备听懂人话。

### 你能得到什么

| 场景 | 小爱原版 | 接上 Claude 后 |
|------|---------|---------------|
| "准备睡觉了" | "没学会" | 匹配米家"睡眠模式" → 触发 |
| "开客厅灯、关空调" | 只做第一个 | 分两条，各自匹配 → 触发两个场景 |
| "关窗帘、关灯、明天天气" | 彻底懵 | 匹配两个场景 + 回答天气 |
| "空调26度" | 经常听错 | 匹配米家"空调26度" → 触发 |
| "今天天气" | "还在学习" | 直接回答 |

> 🎯 **一句话里多个事**：Claude 会切成单条，每条匹配一个米家场景，全执行完。  
> 你在米家配了什么，Claude 就能触发什么。没匹配的就回"没找到"。

## 🚀 快速开始

### 方案一：零成本（用小爱音箱）
只需 15 分钟，不花一分钱：👉 [方式一教程](./way1-ha-assist/README.md)

### 方案二：专属硬件（树莓派）
做一个独立的 Claude 语音终端：👉 [方式二教程](./way2-local-voice-node/README.md)

## 📦 两种方式对比

| 对比项 | 方式一（小爱音箱） | 方式二（树莓派终端） |
|--------|------------------|-------------------|
| **额外成本** | **¥0**（用已有设备） | **¥600-900** |
| **拾音距离** | 远（小爱 mic 好） | 较远（4 mic 阵列） |
| **唤醒词** | "小爱同学" | "Hey Claude"（可定制） |
| **依赖** | 小爱音箱 + 米家云 | 完全本地自建 |
| **延迟** | 中等（走米家云） | 较低（直连 HA） |
| **搭建时间** | **15 分钟** | **1-2 天** |
| **外观** | 成品音箱 | DIY 外壳/裸板 |
| **适合人群** | 已有小爱，想快速体验 | 爱折腾，想要独立设备 |

## 🗂️ 项目结构

```
claude-smart-home/
├── README.md                          # ← 你现在在看这个
│
├── way1-ha-assist/                    # 方式一：小爱音箱方案
│   ├── README.md                      # 搭建教程
│   ├── claude_system_prompt.md        # 系统提示词（可自定义）
│   ├── pipeline_config.yaml           # HA 配置示例
│   └── custom_components/
│       └── claude_conversation/       # ★ 核心：Claude 自定义组件
│           ├── __init__.py
│           ├── manifest.json
│           └── conversation.py        # 对话代理逻辑（~200行）
│
├── way2-local-voice-node/             # 方式二：树莓派方案
│   ├── README.md                      # 搭建教程
│   ├── scripts/
│   │   └── setup_respeaker.sh         # 一键安装脚本
│   ├── wyoming_config/                # Wyoming 语音服务配置
│   └── 3d_print_case/                 # 3D 打印外壳
│
├── common/                            # 共用文档
│   ├── examples/                      # 场景示例
│   │   ├── 场景一-起床.md
│   │   ├── 场景二-离家.md
│   │   ├── 场景三-看电影.md
│   │   └── 场景四-睡眠.md
│   └── troubleshooting.md             # 故障排查指南
│
└── video-script/                      # 视频教程脚本
    ├── 第一部分-理念和架构.md
    ├── 第二部分-方式一实操.md
    ├── 第三部分-方式二实操.md
    ├── 第四部分-自定义组件代码讲解.md
    └── 第五部分-GitHub一键部署教程.md
```

## ⚙️ 核心原理

```
你说话 → 麦克风收音 → ASR转文字 → Claude API
                                        │
                          ┌─────────────┴─────────────────┐
                          ▼                               ▼
              🏠 匹配已有场景 → 触发 scene.turn_on   💬 通用对话 → 直接回复
              📱 单个设备 → 直接控制                   
                          │                               │
                          └─────────────┬─────────────────┘
                                        ▼
                                  TTS语音播报
```

**流程**：
1. Claude 把你的话切成单条指令
2. 每条在场景列表里找匹配
3. 找到 → 触发 scene.turn_on；没找到 → "没找到"
4. 知识问答/查状态 → 直接回答

> 一句话拆多条，每条匹配一个米家场景，全部触发。你在米家配了什么就能触发什么。

## 📋 你需要准备

### 通用需要
- 一台 7x24 开机的电脑/NUC/NAS（跑 Home Assistant）
- [Claude API Key](https://console.anthropic.com)（在 Anthropic Console 申请）

### 方式一额外需要
- 小爱音箱（任意型号）
- 米家 APP

### 方式二额外需要
- 树莓派 4B/5 + ReSpeaker 4-Mic Array
- 3.5mm 音箱
- 64GB+ SD 卡

## 🧠 自定义提示词

Claude 的行为完全由 system prompt 控制。你可以：

```yaml
claude_conversation:
  api_key: "sk-ant-..."
  system_prompt: |
    你是我的专属家居管家。
    我家有一个"泡茶模式": 开水吧灯、开饮水机插座、播放轻音乐
```

详细指南见 [claude_system_prompt.md](./way1-ha-assist/claude_system_prompt.md)

## 🎬 视频教程

本系列共 5 集，适合边看边搭：

| # | 标题 | 时长 | 链接 |
|---|------|------|------|
| 1 | 理念和架构 | 5-8min | [脚本](./video-script/第一部分-理念和架构.md) |
| 2 | 零成本方案实操 | 10-15min | [脚本](./video-script/第二部分-方式一实操.md) |
| 3 | DIY 硬件终端 | 10-15min | [脚本](./video-script/第三部分-方式二实操.md) |
| 4 | 核心代码讲解 | 8-12min | [脚本](./video-script/第四部分-自定义组件代码讲解.md) |
| 5 | GitHub 一键部署 | 5-8min | [脚本](./video-script/第五部分-GitHub一键部署教程.md) |

## 🔧 常见问题

常见问题汇总在 [troubleshooting.md](./common/troubleshooting.md)，包括：

- Claude 不执行指令怎么办？
- 小爱说"没学会这个技能"？
- 树莓派声卡没声音？
- API Key 失效了？
- 响应太慢？

## 📄 许可证

MIT License — 随便用，随便改，随便做视频。

## 🌟 贡献

欢迎 Issue、PR、Star！如果你做了改进或中文场景扩展，欢迎提交。

---

<p align="center">
  <sub>如果这个项目帮到了你，请点亮 ⭐</sub>
</p>

# 方式一：Home Assistant + 小爱音箱 + Claude

**零硬件成本方案**——用小爱音箱做麦克风和喇叭，所有理解交给 Claude。

## 效果演示

```
你说：           "小爱同学，关客厅灯、关窗帘、关卧室灯、明天天气"
小爱听到：       "哎，我去问问"（或沉默）
↓
Claude 切成 4 条：["关客厅灯", "关窗帘", "关卧室灯", "明天天气"]
↓
场景匹配：
  关客厅灯 → scene.关客厅灯 → 触发
  关窗帘   → scene.关窗帘   → 触发
  关卧室灯 → scene.关卧室灯 → 触发
  明天天气 → 直接回答
↓
小爱播报：       "已执行：关客厅灯、关窗帘、关卧室灯；明天天气是……"
```

> **一句话多个事**：Claude 会切成单条，每条在米家场景列表里找匹配、触发。  
> 知识问答/查天气/看温度 → 直接回答。没匹配的 → "没找到"。

## 你需要什么

| 项目 | 说明 |
|------|------|
| ✅ 小爱音箱 | 任意型号（Pro / Play / 万能遥控版均可）|
| ✅ 常开的电脑/NUC/NAS | 跑 Home Assistant（树莓派也行）|
| ✅ Claude API Key | 在 [console.anthropic.com](https://console.anthropic.com) 申请 |
| ✅ 智能家居设备 | 米家设备或其他支持 HA 的设备 |
| ✅ **米家场景**（可选） | 已有的复合指令会同步到 HA 自动生效 |

## 整体架构

```
你 ──→ 小爱音箱（收音）──→ Home Assistant（Assist Pipeline）
                                          │
                          ┌─────────────────┼─────────────────┐
                          ▼                 ▼                 ▼
                      Whisper(ASR)    Claude(理解+决策)  Edge TTS(播报)
                          │                 │                 │
                          └─────────────────┼─────────────────┘
                                            ▼
                                     HA 执行设备操作
                                            │
                                            ▼
                                    你家设备（灯/空调/窗帘...）
```

## 安装步骤（15 分钟）

### 第一步：装 Home Assistant

如果没有装过，最简单的方式是用 Docker：

```bash
# 旧电脑/服务器上执行
docker run -d \
  --name homeassistant \
  --restart unless-stopped \
  --privileged \
  -p 8123:8123 \
  -v ./config:/config \
  ghcr.io/home-assistant/home-assistant:stable
```

> 如果是树莓派，推荐刷 [HA OS](https://www.home-assistant.io/installation/raspberrypi)，更省事。

装好后浏览器访问 `http://你电脑IP:8123` 完成初始设置。

### 第二步：接入小爱音箱

1. 装 [HACS](https://hacs.xyz/docs/setup/download/)（如果没有的话）
2. HACS → 搜索安装 **Xiaomi Mi Auto**
3. 重启 HA
4. 设置 → 集成 → 添加集成 → 搜索 "Xiaomi Mi Auto"
5. 扫码登录小米账号，选择你的小爱音箱
6. 成功后小爱会出现在 HA 的设备列表中

### 第三步：安装 Claude 自定义组件

1. 把本项目 `custom_components/claude_conversation/` 文件夹复制到你的 HA 配置目录的 `custom_components/` 下
2. 在 `configuration.yaml` 中添加：

```yaml
claude_conversation:
  api_key: "sk-ant-你的API密钥"
```

3. 重启 HA

### 第四步：配置语音管道（Assist Pipeline）

1. HA → 设置 → 语音助手 → Assist Pipeline → 创建新管道
2. 配置三要素：

| 组件 | 推荐方案 | 安装方式 |
|------|---------|---------|
| **语音转文字 (ASR)** | Wyoming Whisper | 加载项商店 → 搜索安装，推荐 large-v3 模型 |
| **对话代理** | Claude Smart Home Assistant | 选中已安装的自定义组件 |
| **文字转语音 (TTS)** | Microsoft Edge TTS | 加载项商店安装，选中文女声 |

3. 保存管道，设为默认

### 第五步：让小爱的语音走 HA

**方法一（推荐）**：在 Xiaomi Mi Auto 集成设置中启用"Conversation"模式，然后在 Assist Pipeline 中把小爱设为语音卫星设备。

**方法二**：在米家 APP 中：
- 小爱音箱 → 小爱训练 → 添加训练
- 用户说：`*`（通配符）
- 小爱回复：留空
- 执行设备：选择 Home Assistant

这样小爱所有语音都会转发到 HA，不再自己尝试理解。

## 进阶配置

### 修改 Claude 的行为

编辑 `system_prompt.md` 中的提示词，可以：

- 添加场景别名映射（比如你想说"困了"也能触发睡眠场景）
- 调整回复风格（更简洁 / 更详细）
- 设置安全限制（禁止操作门锁、燃气等）
- 参考 [claude_system_prompt.md](./claude_system_prompt.md)

### 米家场景自动同步

HA 的 Xiaomi Mi Auto 集成会自动把你米家 APP 里的所有场景/操作同步成 `scene.xxx` 实体。Claude 每次都会读到这个列表。

| 你在米家配的名字 | 你说什么能触发 |
|-----------------|--------------|
| "睡眠模式" | 睡觉了、晚安、困了、我要睡了 |
| "打开客厅灯" | 开灯、打开灯、客厅灯亮、亮一点 |
| "空调26度" | 空调26度、太热了、开空调 |
| "离家模式" | 出门了、拜拜、我走了 |

新增/修改场景后 HA 自动同步，Claude 下次对话就能感知，**无需改任何代码**。

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 小爱说"小爱没学到这个技能" | 小爱在自己理解，没转发到 HA | 检查米家训练计划或 Xiaomi Mi Auto 配置 |
| Claude 说"未找到某某场景" | 米家场景没同步到 HA | 去 HA → 设置 → 实体 搜 scene. 确认场景存在 |
| HA 报错 "401" | API Key 不对 | 检查 configuration.yaml 中的 api_key |
| HA 报错 "timeout" | Claude API 连接超时 | 检查网络能否访问 api.anthropic.com |
| Claude 执行业务但设备没反应 | 场景有 bug 或设备掉线 | 去 HA 手动触发场景看能不能正常工作 |
| 播报声音不好听 | TTS 引擎问题 | 换用 Edge TTS（音质最好） |

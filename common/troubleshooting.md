# 故障排查指南

## 通用问题

### 1. Claude 没有按预期执行指令

**现象**：说了"开灯"，Claude 回了文字"已为您打开灯光"但没有真的开灯

**原因**：Claude 没有调用工具（execute_ha_service），而是直接文字回复了

**解决**：
1. 检查 system prompt 是否包含"使用 execute_ha_service 工具执行操作"的指令
2. 检查 Claude 返回中是否包含 `tool_calls`（看 HA 日志）
3. 如果 Claude 持续不调用工具，在 system prompt 开头加一句强调：
   ```
   重要：任何时候需要操作设备，必须调用 execute_ha_service 工具，不要只回复文字！
   ```

---

### 2. Claude 说"我没有找到这个设备"

**现象**：说了"打开客厅灯"，Claude 回复找不到设备

**原因**：Claude 看到的设备列表中，没有匹配"客厅灯"这个名称的设备

**解决**：
1. 去 HA → 设置 → 实体，查看你的灯的 friendly_name 是什么
2. 可能是叫"客厅吸顶灯"或"客厅主灯"而不是"客厅灯"
3. 可以在 system prompt 中加入别名映射：
   ```
   设备别名列表：
   - 客厅灯 = light.living_room_ceiling
   - 主灯 = light.living_room_ceiling
   - 大灯 = light.living_room_ceiling
   ```

---

### 3. 响应太慢（延迟超过 5 秒）

**原因**：
- ASR (Whisper) 模型太大，树莓派处理慢
- Claude API 网络延迟
- HA 处理队列堵塞

**解决**：
- 树莓派：Whisper 用 medium 或 small 模型代替 large-v3
- 网络：检查能否直连 api.anthropic.com（不用代理时更快）
- HA：检查 CPU 负载是否过高

---

### 4. Claude 的理解不对

**现象**：说"有点冷"，Claude 说"我去给你倒杯热水"而不是调空调

**原因**：system prompt 中的家居控制优先级不够高

**解决**：
在 system prompt 中强化场景映射：
```
## 温度相关映射（严格执行）
- "有点冷" / "太冷了" / "冷死了" → 调高空调温度或开暖气
- "有点热" / "太热了" / "热死了" → 调低空调温度或开风扇
- 不要对这些指令做心理咨询或建议加衣服
```

---

### 5. 操作成功了但小爱没有说话

**现象**：灯开了，但小爱没有播报

**原因**：
- 小爱的"语音播报"没有被触发
- TTS 管道配置不正确

**解决**：
1. 确保 Assist Pipeline 中 TTS 选了有效引擎（Edge TTS 或 Piper）
2. 在米家 APP 中确保小爱的"语音反馈"是开启状态
3. 检查 HA 日志中是否有 TTS 播放的记录

---

## 方式一专有问题（小爱音箱）

### 6. 小爱说"小爱没学到这个技能"

**原因**：语音没有被转发到 HA，而是小爱自己在处理

**解决**：
1. 检查米家 APP → 小爱音箱 → 小爱训练计划
2. 确认训练规则是：用户说 `*` → 执行 HA
3. 或者在 HA 的 Xiaomi Mi Auto 集成中启用 Conversation 模式
4. 重启小爱音箱

### 7. 小爱无法唤醒

**原因**：
- WiFi 断连
- HA 中 Xiaomi Mi Auto 集成掉线

**解决**：
1. 检查小爱是否在线（米家 APP 中）
2. 在 HA 中重新配置 Xiaomi Mi Auto 集成（重新登录小米账号）
3. 重启小爱音箱（拔电源再插）

---

## 方式二专有问题（树莓派语音节点）

### 8. ReSpeaker 没有声音

**原因**：
- 声卡驱动没装好
- 音频输出不是 3.5mm 口

**解决**：
```bash
# 检查声卡
aplay -l
arecord -l

# 设置默认声卡
cat > /etc/asound.conf << 'EOF'
pcm.!default {
  type asym
  capture.pcm "mic"
  playback.pcm "speaker"
}
pcm.mic {
  type hw
  card 1  # 根据 aplay -l 的输出调整
}
pcm.speaker {
  type hw
  card 0  # 树莓派内置 3.5mm
}
EOF
```

### 9. 唤醒词不灵敏（太灵敏）

**参数调整**：
```yaml
# 灵敏度 0-1，越低越不灵敏（减少误触发）
--sensitivity 0.5

# 阈值 0-1，越高越难唤醒（减少误触发）
--threshold 0.5
```

### 10. Whisper 识别不准

**原因**：
- 环境噪音大
- 麦克风位置不对
- 模型太小

**解决**：
- 在 Whsiper 命令中添加：
  ```
  --initial-prompt "以下是家居控制场景的语音指令。常见的指令有：开灯、关灯、调温度、打开窗帘、空调调到26度。"
  ```
- 使用 better 模型（large-v3 最佳）
- 调整麦克风位置，距离人 1-3 米

### 11. Docker 服务无法启动

**解决**：
```bash
# 查看容器日志
docker logs wyoming-porcupine
docker logs wyoming-whisper
docker logs wyoming-piper

# 检查端口占用
netstat -tlnp | grep -E "10200|10300|10400"

# 重启所有服务
cd /opt/wyoming && docker compose restart
```

---

## API / 网络问题

### 12. Claude API Key 失效

**现象**：HA 日志报 `401 Unauthorized` 或 `invalid x-api-key`

**解决**：
1. 登录 [console.anthropic.com](https://console.anthropic.com)
2. 检查 API Key 是否过期
3. 重新生成 Key
4. 更新 configuration.yaml 中的 api_key

### 13. 网络无法访问 Anthropic API

**原因**：国内网络环境下可能无法直接访问 api.anthropic.com

**解决**：
1. 尝试在服务器上配置代理环境变量
2. 或在 configuration.yaml 中设置自定义 api_url（指向代理地址）
3. 使用 Cloudflare Workers 或 nginx 做反向代理

---

## 日志怎么看

```bash
# HA 核心日志（查看 Claude 调用情况）
docker logs homeassistant -f | grep claude_conversation

# 或者直接看 HA 日志文件
tail -f /path/to/ha/config/home-assistant.log | grep claude

# 树莓派语音节点日志
docker logs wyoming-whisper -f
docker logs wyoming-porcupine -f
```

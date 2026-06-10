"""Claude 对话代理 — 智能家居控制 + 通用推理的 Home Assistant 自定义组件。

安装方式：
  1. 把 claude_conversation/ 整个文件夹复制到 HA 的 custom_components/ 目录
  2. 在 configuration.yaml 中添加配置（见下方示例）
  3. 重启 HA
  4. 在 HA → 设置 → 语音助手 → 对话代理 中选择 "Claude Smart Home Assistant"

configuration.yaml 配置示例：
  claude_conversation:
    api_key: "sk-ant-xxxxxxxxxxxx"     # Anthropic API Key（必填）
    api_url: "https://api.anthropic.com/v1/messages"  # （可选，默认这个）
    model: "claude-sonnet-4-20250514"  # （可选，默认最新 Sonnet）
    system_prompt: "..."               # （可选，不填则使用内置默认）
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.components import conversation
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import intent
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import ulid

_LOGGER = logging.getLogger(__name__)

# 域名和配置键
DOMAIN = "claude_conversation"
CONF_API_URL = "api_url"
CONF_MODEL = "model"
CONF_SYSTEM_PROMPT = "system_prompt"
CONF_MAX_TOKENS = "max_tokens"

DEFAULT_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 2048

# ============================================================
# 默认系统提示词 — 这是 Claude 理解智能家居的"大脑"
# ============================================================
DEFAULT_SYSTEM_PROMPT = """你的工作：听懂用户说的话，拆成单条指令，每条在米家场景列表里找匹配，触发。

## 你怎么工作

用户可能一句话说多个事 → 你先切成单条 → 每条在场景列表里找匹配 → 每条触发一次 scene.turn_on。

你的输入里有：
- **可用场景列表**：米家 APP 里的所有场景/操作（scene.xxx），用户的指令都在这里
- **设备状态**：回答问题时参考（如"客厅几度"）

## 规则

1. **一句话有多个指令时，先切分**：
   "关客厅灯、关窗帘、关卧室灯、明天天气" → 切成 ["关客厅灯", "关窗帘", "关卧室灯", "明天天气"]
   然后每个分别处理。

2. **每条指令都在场景列表里找匹配**：找到就用 execute_ha_service 触发 scene.turn_on
   "关客厅灯" → 匹配 scene.关客厅灯 → 触发
   "关窗帘" → 匹配 scene.关窗帘 → 触发
   "明天天气" → 不是场景，直接回答

3. **匹配不上 → 只回"没找到"**，不要自己控制设备

4. **知识问答/查状态 → 直接回答**，不触发场景

## 匹配示例

场景列表中有"关客厅灯"、"关窗帘"、"关卧室灯"、"睡眠模式"、"离家模式"时：
- "关窗帘" → 匹配"关窗帘" → scene.turn_on
- "关卧室灯" → 匹配"关卧室灯" → scene.turn_on
- "关客厅灯、关窗帘、关卧室灯、明天天气" → 触发三个场景 + 回答天气
- "关客厅灯关窗帘关卧室灯"（没标点）→ 同样切成三条分别匹配
- "准备睡觉了" → 匹配"睡眠模式" → scene.turn_on
- "今天天气怎么样" → 直接回答
- "客厅多少度" → 读状态回答

## 回复风格
- 触发多个场景时："已执行：关客厅灯、关窗帘、关卧室灯；明天天气是..."
- 触发单个场景时："已执行睡眠模式"
- 没匹配："没找到对应的操作"
- 对话直接回答"

# ============================================================
# Claude 工具定义 — execute_ha_service
# 这是 HA 暴露给 Claude 的唯一工具接口
# ============================================================
HA_SERVICE_TOOL = {
    "name": "execute_ha_service",
    "description": "触发米家场景：domain='scene', service='turn_on', entity_id='scene.xxx'。如果用户有多个指令，每条指令调用一次此工具，多次调用之间不分先后。",
    "input_schema": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "固定填 scene"
            },
            "service": {
                "type": "string",
                "description": "固定填 turn_on"
            },
            "entity_id": {
                "type": "string",
                "description": "要触发的场景 ID，如 scene.sleep_mode"
            }
        },
        "required": ["domain", "service", "entity_id"]
    }
}


async def async_setup(hass: HomeAssistant, config: dict):
    """初始化 Claude 对话代理。

    从 configuration.yaml 读取配置，注册为 HA 的对话代理。
    """
    conf = config.get(DOMAIN)
    if conf is None:
        _LOGGER.debug("未找到 %s 配置，跳过初始化", DOMAIN)
        return True

    api_key = conf.get(CONF_API_KEY, "")
    if not api_key:
        _LOGGER.error("缺少 api_key，请在 configuration.yaml 中配置 claude_conversation.api_key")
        return False

    api_url = conf.get(CONF_API_URL, DEFAULT_API_URL)
    model = conf.get(CONF_MODEL, DEFAULT_MODEL)
    system_prompt = conf.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)
    max_tokens = conf.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

    _LOGGER.info(
        "Claude Smart Home Agent 初始化: model=%s, api_url=%s",
        model, api_url
    )

    agent = ClaudeConversationAgent(
        hass=hass,
        api_key=api_key,
        api_url=api_url,
        model=model,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
    )

    conversation.async_set_agent(hass, agent)
    _LOGGER.info("Claude Smart Home Agent 已注册为默认对话代理")

    return True


class ClaudeConversationAgent(conversation.AbstractConversationAgent):
    """Claude 对话代理类。

    接收用户语音/文字输入 → 获取设备状态 → 调用 Claude API →
    解析响应（文字回复 + 工具调用）→ 执行工具调用 → 返回结果给用户。
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        api_url: str,
        model: str,
        system_prompt: str,
        max_tokens: int = 1024,
    ):
        self.hass = hass
        self._api_key = api_key
        self._api_url = api_url
        self._model = model
        self._system_prompt = system_prompt
        self._max_tokens = max_tokens
        # 对话历史缓存 {conversation_id: [messages]}
        self._history: dict[str, list[dict]] = {}
        # 历史时间戳，用于 TTL 清理
        self._history_ts: dict[str, float] = {}
        self._history_ttl = 3600  # 1 小时后自动清理

    @property
    def attribution(self):
        return {"name": "Claude Smart Home", "url": "https://anthropic.com"}

    # ---------------------------------------------------------------
    # 核心方法：处理用户输入
    # ---------------------------------------------------------------
    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """处理用户输入 —— 整个流程的主入口。"""
        conv_id = user_input.conversation_id or ulid.ulid_now()

        # 定期清理过期历史
        self._cleanup_history()

        # 1. 获取当前设备状态，注入给 Claude
        device_context = await self._build_device_context()

        # 2. 构建消息
        user_message = (
            f"--- 当前设备状态 ---\n"
            f"{device_context}\n\n"
            f"--- 用户指令 ---\n"
            f"{user_input.text}"
        )

        messages = []
        # 添加历史（保留最近 3 轮）
        if conv_id in self._history:
            messages.extend(self._history[conv_id][-6:])  # 3轮=6条消息
        messages.append({"role": "user", "content": user_message})

        # 3. 调用 Claude API
        try:
            response_text, tool_calls_list = await self._call_claude(messages)
        except Exception as e:
            _LOGGER.error("调用 Claude API 失败: %s", e)
            intent_resp = intent.IntentResponse(language=user_input.language)
            intent_resp.async_set_speech("抱歉，我暂时无法连接到 AI 服务，请检查网络或 API Key 配置。")
            return conversation.ConversationResult(
                response=intent_resp,
                conversation_id=conv_id,
            )

        # 4. 保存历史
        assistant_msg = {"role": "assistant", "content": response_text or "已执行"}
        if tool_calls_list:
            assistant_msg["tool_calls"] = tool_calls_list
        messages.append(assistant_msg)
        self._history[conv_id] = messages[-10:]  # 最多保留 5 轮
        self._history_ts[conv_id] = time.time()

        intent_resp = intent.IntentResponse(language=user_input.language)

        # 5. 执行工具调用（如果 Claude 决定调用设备控制）
        if tool_calls_list:
            execution_results = []
            for tc in tool_calls_list:
                result = await self._execute_ha_service(tc)
                execution_results.append(result)

            # 汇总结果
            success_count = sum(1 for r in execution_results if r["success"])
            fail_count = len(execution_results) - success_count

            display_text = response_text or f"已执行 {success_count} 个操作"
            if fail_count > 0:
                display_text += f"，其中 {fail_count} 个操作失败"

            intent_resp.async_set_speech(display_text)
        else:
            # 纯对话回复
            intent_resp.async_set_speech(response_text or "好的")

        return conversation.ConversationResult(
            response=intent_resp,
            conversation_id=conv_id,
        )

    # ---------------------------------------------------------------
    # 对话历史管理
    # ---------------------------------------------------------------
    def _cleanup_history(self):
        """清理过期的对话历史，防止内存泄漏。"""
        now = time.time()
        expired = [
            cid for cid, ts in self._history_ts.items()
            if now - ts > self._history_ttl
        ]
        for cid in expired:
            self._history.pop(cid, None)
            self._history_ts.pop(cid, None)
        if expired:
            _LOGGER.debug("清理 %d 条过期对话历史", len(expired))

    # ---------------------------------------------------------------
    # 构建设备上下文
    # ---------------------------------------------------------------
    async def _build_device_context(self) -> str:
        """获取 HA 中所有设备的状态，格式化为 Claude 易读的文本。"""
        states: list[State] = self.hass.states.async_all()

        # ---- 第一部分：收集可用场景 ----
        scene_list: list[str] = []
        script_list: list[str] = []
        device_list: list[str] = []

        entity_registry = er.async_get(self.hass)
        area_registry = ar.async_get(self.hass)

        for state in states:
            # 收集场景（Scene）
            if state.domain == "scene":
                name = state.attributes.get('friendly_name', state.entity_id)
                scene_list.append(f"  • {name} ({state.entity_id})")
                continue

            # 收集脚本（可能由米家联动生成）
            if state.domain == "script":
                name = state.attributes.get('friendly_name', state.entity_id)
                script_list.append(f"  • {name} ({state.entity_id})")
                continue

            # 跳过其他不必要实体
            skip_domains = {
                "automation", "zone", "group",
                "input_boolean", "input_number", "input_select", "input_text",
                "timer", "counter", "proximity", "sun", "binary_sensor",
            }
            if state.domain in skip_domains:
                continue
            # 跳过不可用的设备
            if state.state in ("unavailable", "unknown", "none"):
                continue

            entry = entity_registry.async_get(state.entity_id)
            area_name = None
            if entry and entry.area_id:
                area = area_registry.async_get_area(entry.area_id)
                if area:
                    area_name = area.name

            line = f"  • {state.attributes.get('friendly_name', state.entity_id)}" \
                   f" ({state.entity_id}): {state.state}"
            # 添加主要属性
            attrs = {}
            for key in ("brightness", "temperature", "current_temperature",
                        "humidity", "volume_level", "position", "wind_speed",
                        "preset_mode", "color_mode"):
                if key in state.attributes:
                    attrs[key] = state.attributes[key]
            if attrs:
                line += f" [{', '.join(f'{k}={v}' for k, v in attrs.items())}]"

            if area_name:
                device_list.append(f"  [{area_name}] {line.lstrip()}")
            else:
                device_list.append(line)

        # ---- 组装文本 ----
        parts = []

        # 场景列表放最前面
        if scene_list:
            parts.append("【可用场景（Scene）】")
            parts.extend(scene_list)
            parts.append("")

        if script_list:
            parts.append("【可用脚本（Script）】")
            parts.extend(script_list)
            parts.append("")

        # 设备列表
        if device_list:
            parts.append("【设备状态】")
            parts.extend(device_list)

        context = "\n".join(parts) if parts else "（暂无可用设备或场景）"
        return context

    # ---------------------------------------------------------------
    # 调用 Claude API
    # ---------------------------------------------------------------
    async def _call_claude(self, messages: list[dict]) -> tuple[str | None, list[dict] | None]:
        """调用 Anthropic Claude API，返回 (回复文本, 工具调用列表)。

        支持自动重试：网络错误/超时最多重试 2 次，4xx 错误不重试。
        """
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": self._system_prompt,
            "messages": messages,
            "tools": [HA_SERVICE_TOOL],
        }

        timeout = aiohttp.ClientTimeout(total=60)
        max_retries = 2
        retry_delay = 1.0

        result = None
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self._api_url,
                        headers=headers,
                        json=payload,
                        timeout=timeout,
                    ) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            _LOGGER.error(
                                "Claude API 返回错误 [%s]: %s",
                                resp.status, error_text[:500],
                            )
                            # 4xx 客户端错误不重试（Key 无效、参数错误等）
                            if 400 <= resp.status < 500:
                                return f"API 请求失败 (HTTP {resp.status})", None
                            # 5xx 服务端错误抛异常进入重试
                            raise aiohttp.ClientError(
                                f"HTTP {resp.status}: {error_text[:200]}"
                            )

                        result = await resp.json()
                        break  # 成功，跳出重试循环

            except asyncio.TimeoutError:
                last_error = "请求超时"
                _LOGGER.warning(
                    "Claude API 超时 (尝试 %d/%d)",
                    attempt + 1, max_retries + 1,
                )
            except aiohttp.ClientError as e:
                last_error = str(e)[:300]
                _LOGGER.warning(
                    "Claude API 错误 (尝试 %d/%d): %s",
                    attempt + 1, max_retries + 1, e,
                )

            if attempt < max_retries:
                await asyncio.sleep(retry_delay * (attempt + 1))
        else:
            # 所有重试均失败
            _LOGGER.error("Claude API 调用最终失败: %s", last_error)
            return "服务暂时不可用，请稍后再试", None

        # 解析响应
        response_text = None
        tool_calls = []

        for content_block in result.get("content", []):
            if content_block.get("type") == "text":
                response_text = content_block.get("text", "")

            elif content_block.get("type") == "tool_use":
                tool_calls.append({
                    "id": content_block.get("id"),
                    "name": content_block.get("name"),
                    "input": content_block.get("input", {}),
                })

        if response_text:
            response_text = response_text.strip() or None

        return response_text, tool_calls if tool_calls else None

    # ---------------------------------------------------------------
    # 执行 HA 服务
    # ---------------------------------------------------------------
    async def _execute_ha_service(self, tool_call: dict) -> dict:
        """执行 Claude 请求的 HA 服务调用。

        支持通过 entity_id 或 area（区域）指定目标设备。
        """
        name = tool_call.get("name")
        if name != "execute_ha_service":
            return {"success": False, "error": f"未知工具: {name}"}

        params = tool_call.get("input", {})
        domain = params.get("domain")
        service = params.get("service")
        entity_id = params.get("entity_id")
        area_name = params.get("area")
        data = params.get("data", {})

        if not domain or not service:
            return {"success": False, "error": "缺少 domain 或 service 参数"}

        # 如果指定了区域，自动查找该区域下的设备
        target_entities = []
        if entity_id:
            target_entities = [e.strip() for e in entity_id.split(",") if e.strip()]
        elif area_name:
            target_entities = await self._find_entities_by_area(area_name, domain)

        service_data = data.copy()

        if target_entities:
            service_data["entity_id"] = target_entities

        try:
            await self.hass.services.async_call(
                domain=domain,
                service=service,
                service_data=service_data,
                blocking=True,
                limit=3.0,  # 3 秒超时
            )
            _LOGGER.info(
                "执行设备操作: %s.%s entity=%s data=%s",
                domain, service, target_entities, data,
            )
            return {
                "success": True,
                "domain": domain,
                "service": service,
                "entities": target_entities,
            }
        except Exception as e:
            _LOGGER.error("执行操作失败 %s.%s: %s", domain, service, e)
            return {
                "success": False,
                "error": str(e),
                "domain": domain,
                "service": service,
            }

    # ---------------------------------------------------------------
    # 按区域查找设备
    # ---------------------------------------------------------------
    async def _find_entities_by_area(self, area_name: str, domain: str | None = None) -> list[str]:
        """根据区域名称和可选的域，查找匹配的实体 ID 列表。"""
        entity_registry = er.async_get(self.hass)
        area_registry = ar.async_get(self.hass)

        # 查找区域
        target_area = None
        for area in area_registry.async_list_areas():
            if area.name == area_name or area_name in area.name:
                target_area = area
                break

        if not target_area:
            _LOGGER.warning("未找到区域: %s", area_name)
            return []

        entities = []
        for entry in entity_registry.entities.values():
            if entry.area_id != target_area.area_id:
                continue
            if domain and entry.entity_id.split(".")[0] != domain:
                continue
            entities.append(entry.entity_id)

        return entities

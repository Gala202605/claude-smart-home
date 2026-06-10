# 视频第五集：GitHub 开源——5 分钟部署你自己的 Claude 智能管家

**时长**：5-8 分钟
**风格**：快速、实用、面向开发者

---

## 开场（0:00-0:30）

**[旁白]**：最后一期了！前面四期我们从架构到实操到代码全部讲完了。这期把整个项目打包，让大家能在 5 分钟内从零部署起来。

**[画面]**：展示 GitHub 仓库页面
```
github.com/你的用户名/claude-smart-home
⭐ 已获 xxx Stars
```

**[旁白]**：项目的完整代码已经开源，包括自定义组件、配置脚本、文档、视频脚本。你只需要几步就能用起来。

---

## 项目结构（0:30-1:30）

**[画面]**：展示 GitHub 上的目录树

```
claude-smart-home/
├── README.md                     ← 项目说明 + 快速开始
├── way1-ha-assist/               ← 方式一：用小爱
│   ├── custom_components/        ← Claude 自定义组件
│   ├── claude_system_prompt.md   ← 提示词模板
│   └── pipeline_config.yaml      ← 配置示例
├── way2-local-voice-node/        ← 方式二：做硬件
│   ├── scripts/setup_respeaker.sh ← 一键安装脚本
│   └── 3d_print_case/            ← 3D 打印文件
├── common/                       ← 文档
│   ├── examples/                 ← 场景示例
│   └── troubleshooting.md        ← 排错指南
└── video-script/                 ← 视频脚本
```

**[旁白]**：不废话，直接告诉大家怎么用。

---

## 快速部署：方式一（1:30-3:30）

**[画面]**：分步骤展示

### 第一步：安装 Claude 组件

```bash
# SSH 到你的 HA 服务器
cd /path/to/ha_config
mkdir -p custom_components
cd custom_components

# 直接从 GitHub 下载
wget https://github.com/你的用户名/claude-smart-home/archive/refs/heads/main.zip
# 解压后把 claude_conversation 文件夹放到 custom_components/
```

**[旁白]**：或者打开项目，直接把 `way1-ha-assist/custom_components/claude_conversation/` 整个文件夹复制到 HA 的 `custom_components/` 下面。

### 第二步：加一行配置

```yaml
# configuration.yaml 中添加
claude_conversation:
  api_key: "sk-ant-你的密钥"
```

### 第三步：重启 HA

```bash
docker restart homeassistant
```

**[旁白]**：然后去 HA 的 Assist Pipeline 选 Claude，就搞定了。

**[画面]**：计时器
```
从零开始 → 配置完成
⏱️ 不到 5 分钟
```

---

## 快速部署：方式二（3:30-5:00）

**[画面]**：

```bash
# 树莓派上执行（脚本会自动生成第二部分）
wget https://raw.githubusercontent.com/你的用户名/claude-smart-home/main/way2-local-voice-node/scripts/setup_respeaker.sh

chmod +x setup_respeaker.sh
sudo ./setup_respeaker.sh
# 等待自动重启（脚本会自动生成 setup_part2.sh）
sudo ./setup_part2.sh
```

> 💡 `setup_part2.sh` 由 `setup_respeaker.sh` 首次运行时自动生成，
> 不需要单独下载。

**[旁白]**：两个命令，树莓派语音节点就配好了。

---

## 如何贡献/自定义（5:00-6:30）

**[旁白]**：这个项目是开源的，欢迎大家二改。

### 改提示词
```yaml
# 在 configuration.yaml 中
claude_conversation:
  api_key: "..."
  system_prompt: "你自己的提示词..."  # 覆盖默认提示词
```

### 添加新场景
在 system prompt 中添加：
```
## 我家专属场景
- "我要泡澡" → 关主灯、开氛围灯、放轻音乐、热水器预热
```

### PR/Issue
欢迎大家提 Issue 和 Pull Request，一起把这个项目做得更好。

---

## 做视频的伙伴（6:30-7:30）

**[旁白]**：如果你也做视频，想把这个项目做成教程，完全没问题。所有视频脚本也在项目里，在 `video-script/` 目录下。

**[画面]**：展示 video-script 目录

**[旁白]**：可以直接拿来用，按你的风格调整。我会持续更新版本和脚本。

---

## 结尾（7:30-结束）

**[旁白]**：五集下来，我们从"小爱很笨"聊到了做一个完整的 Claude 智能家居管家。

回顾一下：
- 第一集：理念——为什么做
- 第二集：方案一——零成本用小爱
- 第三集：方案二——自己做硬件
- 第四集：代码——怎么工作的
- 第五集：开源——5 分钟一键部署

**[画面]**：GitHub 二维码

**[旁白]**：Star、Fork、Issue，都欢迎。项目地址在评论区置顶。

**[画面]**：下一期预告
```
下个系列预告：
用 Claude 做智能家居自动化脚本—— 
让家学会自己思考
```

**[旁白]**：感谢五期的陪伴，我们下个系列见！

---

## 备注

- 这期节奏快，主要展示"有多简单"而不是"怎么做"
- GitHub 页面要有好的 README 封面图
- 二维码放在视频结尾，方便手机扫码
- 全系列完结撒花 🎉

# 👁️ Claude Vision — 让 Claude 看见世界

> **给无原生视觉能力的 LLM 装上眼睛**：截图、UI 还原、OCR、双图对比、硬件照片识别——全部通过豆包视觉（火山方舟 Ark）自动搞定。

一个从"模型看不到图"的痛苦经历，打磨成"发图即自动分析"的完整解决方案。

---

## 🚀 30 秒复制：给其他 Agent 的速成 Prompt

> 把下面这段直接粘贴给任何 Agent（Claude / ChatGPT / 其他），它就能快速学会这套视觉能力：

```
你是我的视觉分析助手。本环境模型可能无法直接看图，你需要：
1. 用 `vision_doubao.py` 脚本调用豆包视觉（火山方舟 Ark）分析图片
2. key 获取优先级：环境变量 ARK_API_KEY → 1Password op CLI（OP_REF 引用）→ 报错
3. 用户上传任何图片/截图/PDF → 自动分析，不要问"要不要看图"，不要报 "unsupported file"
4. 图片在 uploads 目录，用 bash 去找（ls /sessions/*/mnt/uploads/）
5. 模式选择：UI截图=A 还原；界面bug=B；报错日志=C；文字表格=D；实物照片=E；双图对比=compare
6. 大图先压缩到长边 1280（2.1-pro 深度思考大图会超时）；webp 转 JPEG；PDF 先转图
7. 跑脚本前清代理：unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy NO_PROXY no_proxy
8. 默认用 doubao-seed-2-1-pro（质量优先），批量用 --model doubao-seed-2-0-mini

用法：
  python3 vision_doubao.py <图> A "指令"   # UI还原
  python3 vision_doubao.py <图> B          # 问题定位
  python3 vision_doubao.py <图> C          # 错误日志提取
  python3 vision_doubao.py <图> D          # OCR
  python3 vision_doubao.py <图> E "指令"   # 通用描述
  python3 vision_doubao.py compare a b "指令"  # 双图对比
```

**复制以上 Prompt + 下载 `vision_doubao.py`，你就拥有了完整的视觉分析能力。**

---

## 💡 为什么做这个

### 问题：模型看不见图

本环境模型（Haiku 4.5）**没有可靠的内置看图能力**。用户每次上传图片，模型都会显示：

> `[Unsupported Image]` / "I can't see the image"

这对需要看图工作的用户（UI 设计、硬件开发、文档 OCR）是灾难。

### 解决方案：外挂视觉层

既然模型自己没有眼睛，那就给它**装一副外部眼睛**——调用**豆包视觉模型**（火山方舟 Ark API）看图，返回文字描述。

```
用户发图 → Claude 脚本调豆包视觉 → 返回结构化文字 → Claude 理解并回复
```

---

## 📚 经历时间线（踩坑记录）

| 时间 | 阶段 | 关键决策/踩坑 |
|------|------|--------------|
| 2026-08-08 | **Qwen 时代** | 用 Qwen3-VL-flash 当视觉层，DashScope API。实测 OCR/日志提取准确 |
| 2026-08-08 | **发现幻觉** | Qwen3-VL-flash **双图对比有幻觉倾向**——虚构不存在的差异，结果只能当"待核验清单" |
| 2026-08-10 | **换豆包** | 用户决策换豆包。评估 doubao-seed-1.6-vision vs 2.0-mini vs **2.1-pro** |
| 2026-08-10 | **定双模型** | 2.1-pro（质量优先，深度思考）为主 + 2-0-mini（批量快档）兜底 |
| 2026-08-11 | **1Password 集成** | key 从手动贴 → op CLI 自动取 → 技能内联 token，任何会话可用 |
| 2026-08-11 | **GitHub 发布** | 代码通用化（去硬编码），推到 monah-studio/claude-vision |

### 关键踩坑清单

1. **Qwen3-VL-flash 双图幻觉** → 换豆包 2.1-pro（深度思考，更稳）
2. **大图 + 深度思考超时** → 脚本自动压缩 >2048px；建议先压到 1280
3. **webp 直传被拒** → 转 JPEG（PIL convert RGB）
4. **沙箱代理畸形 IPv6** → 跑前必须 `unset ...proxy...`，否则 HTTP 库崩
5. **`op read` 标题含空格/括号解析失败** → 一律用条目 ID
6. **技能 base64 损坏** → 重新生成时验证解码一致

---

## ✨ 最终方案

### 架构

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   用户发图    │ ──▶ │  Claude Agent     │ ──▶ │ 豆包视觉 2.1-pro   │
│ (uploads目录) │     │ (无内置视觉能力)    │     │ (火山方舟 Ark)     │
└─────────────┘     └──────────────────┘     └──────────────────┘
                           │  ▲
                           ▼  │
                    ┌──────────────────┐
                    │  1Password 取 key │
                    │ (op CLI 自动)      │
                    └──────────────────┘
```

### 核心能力

| 能力 | 说明 |
|------|------|
| 🖼️ **5 种识别模式** | UI 还原 / 问题定位 / 日志提取 / OCR / 通用描述 |
| 🔄 **双图对比** | 找差异，防止幻觉 |
| 📦 **自动压缩** | >2048px 自动缩放，避免 API 过大 |
| 🔑 **自动取 key** | 环境变量 → 1Password op → 明确报错，不硬编码 |
| 🚀 **双模型** | 质量优先（深度思考）+ 批量快档（低延迟） |
| 🪶 **零依赖** | 纯 Python 标准库 + Pillow |

### 技术栈

- **视觉模型**：Doubao Seed 2.1 Pro（`doubao-seed-2-1-pro-260628`）/ 2.0 Mini
- **API**：火山方舟 Ark（OpenAI 兼容）
- **凭据**：1Password CLI（`op`）+ Service Account token
- **语言**：Python 3.8+（urllib + Pillow）

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install Pillow
```

### 2. 配置 API Key（二选一）

```bash
# 方式一：环境变量
export ARK_API_KEY="ark-..."

# 方式二：1Password（推荐）
# op read "op://Claude Code/Ark API Key (豆包视觉)/credential"
```

### 3. 分析第一张图

```bash
python3 vision_doubao.py your_image.png E "描述这张图"
```

---

## 📖 使用手册

### 模式速查

| 模式 | 用途 | 示例 |
|------|------|------|
| `A` | **UI 像素级还原**：布局/坐标/色值/字号 | `vision_doubao.py ui.png A "还原页面"` |
| `B` | **问题定位**：界面 bug/错位/重叠 | `vision_doubao.py bug.png B` |
| `C` | **错误日志提取**：报错/堆栈逐字 | `vision_doubao.py error.png C` |
| `D` | **OCR**：文字逐字提取 | `vision_doubao.py doc.png D` |
| `E` | **通用描述**：实物/场景/照片 | `vision_doubao.py photo.jpg E` |
| `compare` | **双图对比**：找真实差异 | `vision_doubao.py compare a.png b.png` |

### 模型切换

```bash
# 质量优先（默认）
python3 vision_doubao.py img.png E

# 批量快档
python3 vision_doubao.py img.png D --model doubao-seed-2-0-mini-260428

# 环境变量
export ARK_MODEL="doubao-seed-2-0-mini-260428"
```

### 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `ARK_API_KEY` | — | 火山方舟 key（最高优先） |
| `ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3/chat/completions` | API 端点 |
| `ARK_MODEL` | `doubao-seed-2-1-pro-260628` | 默认模型 |
| `OP_REF` | `op://Claude Code/Ark API Key (豆包视觉)/credential` | 1Password 引用 |

---

## 🔁 自动化工作流

### UI 像素级还原闭环

```
设计图 → 豆包视觉 A 分析 → 写 HTML/CSS → 截图 → compare 双图对比 → 修正 → 对齐
```

### 发图自动分析

配置 Claude 记忆规则后，**用户发图 → Agent 自动分析**，无需手动触发：
- 自动找 uploads 目录
- 自动选模式（拿不准用 E）
- 自动压缩/转格式
- 结果直接呈现

---

## ⚠️ 常见问题

| 问题 | 解决 |
|------|------|
| 大图超时 | 先压缩到长边 1280 |
| webp 被拒 | 转 JPEG |
| 代理报错 `Invalid port` | `unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy NO_PROXY no_proxy` |
| 401 key 失效 | 检查火山方舟控制台 key/欠费 |
| 429 限流 | 稍后重试 |
| 403 无权限 | 换模型 |

---

## 🤝 致谢

源于一次"模型看不到图"的真实痛点，经过数轮迭代打磨。感谢 Doubao Seed 提供强大的视觉理解能力，感谢 1Password 提供安全的凭据管理。

---

## 📄 License

MIT — 自由使用、修改、分享。

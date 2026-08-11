# claude-vision

给 Claude（及其他无原生视觉能力的 LLM）提供**图片理解能力**——通过调用豆包视觉模型（火山方舟 Ark）看图。

模型本身不支持看图的场景（截图 / UI 还原 / OCR / 双图对比 / 硬件照片识别），用这个脚本把图片喂给豆包视觉，拿到结构化文字描述。

## 功能

- **5 种识别模式 + 双图对比**，覆盖常见看图需求
- **自动压缩**：图片超过 2048px 长边自动缩放，避免 API 请求过大
- **自动取 key**：环境变量 → 1Password op CLI → 明确报错，不硬编码密钥
- **双模型**：质量优先（深度思考）与快速批量（低延迟）按需切换
- **零第三方依赖**：纯 Python 标准库（`urllib` + `PIL`）

## 环境要求

- Python 3.8+
- Pillow（图片处理）：`pip install Pillow`
- 火山方舟（Ark）API key，或已配置 1Password CLI（`op`）

## 安装

```bash
# 1. 安装依赖
pip install Pillow

# 2. 获取 API key（二选一）
export ARK_API_KEY="ark-..."                        # 方式一：环境变量

# 方式二：1Password op CLI（默认引用 op://Claude Code/Ark API Key (豆包视觉)/credential）
op read "op://Claude Code/Ark API Key (豆包视觉)/credential"   # 验证可取到 key
# 自定义引用：export OP_REF="op://你的Vault/条目/字段"
```

## 用法

```bash
python3 vision_doubao.py <图片> <模式> ["额外指令"]
```

### 模式

| 模式 | 用途 | 例子 |
|------|------|------|
| `A` | UI 像素级还原（布局/坐标/色值/字号） | `python3 vision_doubao.py ui.png A "还原这个页面"` |
| `B` | 问题定位（界面 bug / 错位 / 重叠） | `python3 vision_doubao.py bug.png B` |
| `C` | 错误日志 / 堆栈逐字提取 | `python3 vision_doubao.py error.png C` |
| `D` | OCR 文字提取（逐字，保留原文） | `python3 vision_doubao.py doc.png D` |
| `E` | 通用描述（实物 / 场景 / 照片） | `python3 vision_doubao.py photo.jpg E "描述这个设备"` |
| `compare` | 双图对比找差异 | `python3 vision_doubao.py compare a.png b.png "关注差异"` |

模式省略时默认 `E`（通用描述）。

### 模型切换

```bash
# 默认：doubao-seed-2-1-pro-260628（质量优先，深度思考，更准但慢）
python3 vision_doubao.py img.png E

# 批量：doubao-seed-2-0-mini-260428（低时延高并发，适合跑量 OCR / 扫图）
python3 vision_doubao.py img.png D --model doubao-seed-2-0-mini-260428

# 或环境变量指定
export ARK_MODEL="doubao-seed-2-0-mini-260428"
```

模型优先级：`--model` 参数 > `ARK_MODEL` 环境变量 > 默认 `doubao-seed-2-1-pro`。

## 配置项（环境变量）

| 变量 | 默认 | 说明 |
|------|------|------|
| `ARK_API_KEY` | — | 火山方舟 API key（最高优先级） |
| `ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3/chat/completions` | API 端点 |
| `ARK_MODEL` | `doubao-seed-2-1-pro-260628` | 默认模型 |
| `OP_REF` | `op://Claude Code/Ark API Key (豆包视觉)/credential` | 1Password 引用 |

## 典型工作流：UI 像素级还原

1. 设计图 → `vision_doubao.py ui.png A` 分析布局/坐标/色值
2. 根据分析写 HTML/CSS
3. 截图实际效果 → `vision_doubao.py compare spec.png real.png` 双图对比
4. 按差异清单修正，重复直到对齐

## 注意

- 大图（>1500px）+ 深度思考模型可能慢——建议先压缩到长边 1280
- webp 图片直传可能被服务端拒绝——先转 JPEG
- 遇到代理/防火墙环境，可能需要配置网络直连

## 模型说明

- **doubao-seed-2-1-pro**：字节 Seed 2.1 系列旗舰，全模态，深度思考机制让复杂视觉理解（UI/文档/双图）更稳、幻觉更少
- **doubao-seed-2-0-mini**：低时延高并发，适合大批量简单识别

## License

MIT

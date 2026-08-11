# 👁️ Claude Vision — Give Claude Eyes

> **Give vision capabilities to LLMs without native image understanding**: screenshots, UI reproduction, OCR, image comparison, hardware photo recognition — all handled automatically through the Doubao vision model (Volcano Engine Ark).

A complete solution refined from the painful experience of "the model can't see images" to "upload an image and get instant analysis."

---

## 🚀 30-Second Replication: Quick-Start Prompt for Other Agents

> Paste this to any Agent (Claude / ChatGPT / others), and it can quickly learn this vision capability:

```
You are my vision analysis assistant. This environment's model may not be able to see images directly, so you need to:
1. Use the `vision_doubao.py` script to call the Doubao vision model (Volcano Engine Ark) to analyze images
2. Key resolution order: env var ARK_API_KEY → 1Password op CLI (OP_REF reference) → error
3. When user uploads any image/screenshot/PDF → analyze automatically; don't ask "want me to look?", don't report "unsupported file"
4. Images live in the uploads directory — find them with bash (ls /sessions/*/mnt/uploads/)
5. Mode selection: UI screenshot=A (reproduce); buggy UI=B; error log=C; text/table=D; physical photo=E; image comparison=compare
6. Downscale large images to 1280px first (2.1-pro deep-thinking times out on big images); convert webp to JPEG; convert PDF to image first
7. Clear proxy before running: unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy NO_PROXY no_proxy
8. Default to doubao-seed-2-1-pro (quality-first); use --model doubao-seed-2-0-mini for batch

Usage:
  python3 vision_doubao.py <img> A "instruction"   # UI reproduction
  python3 vision_doubao.py <img> B                 # problem location
  python3 vision_doubao.py <img> C                 # error log extraction
  python3 vision_doubao.py <img> D                 # OCR
  python3 vision_doubao.py <img> E "instruction"   # general description
  python3 vision_doubao.py compare a b "instruction"  # image comparison
```

**Copy the prompt above + download `vision_doubao.py` and you have a complete vision analysis capability.**

---

## 💡 Why This Exists

### The Problem: The Model Can't See

This environment's model (Haiku 4.5) has **no reliable built-in image understanding**. Every time a user uploads an image, the model shows:

> `[Unsupported Image]` / "I can't see the image"

That's devastating for users who need to work with images (UI design, hardware development, document OCR).

### The Solution: An External Vision Layer

Since the model has no eyes, give it an **external pair of eyes** — call the **Doubao vision model** (Volcano Engine Ark API) to see the image and return a text description.

```
User uploads image → Claude script calls Doubao vision → returns structured text → Claude understands and replies
```

---

## 📚 Journey Timeline (Lessons Learned)

| Date | Stage | Key Decision / Pitfall |
|------|-------|----------------------|
| 2026-08-08 | **Qwen era** | Used Qwen3-VL-flash as vision layer via DashScope API. OCR/log extraction was accurate |
| 2026-08-08 | **Found hallucination** | Qwen3-VL-flash **hallucinates in image comparison** — fabricates non-existent differences; results only usable as a "verification checklist" |
| 2026-08-10 | **Switched to Doubao** | User decided to switch. Evaluated doubao-seed-1.6-vision vs 2.0-mini vs **2.1-pro** |
| 2026-08-10 | **Dual-model decision** | 2.1-pro (quality-first, deep thinking) as primary + 2-0-mini (batch speed) as fallback |
| 2026-08-11 | **1Password integration** | Key flow: manual paste → op CLI auto-fetch → token inlined in skill, usable from any session |
| 2026-08-11 | **GitHub release** | Code generalized (removed hardcoding), pushed to monah-studio/claude-vision |

### Key Pitfall Checklist

1. **Qwen3-VL-flash image-comparison hallucination** → switched to Doubao 2.1-pro (deep thinking, more stable)
2. **Big image + deep thinking timeout** → script auto-downscales >2048px; recommend downscaling to 1280 first
3. **webp rejected** → convert to JPEG (PIL convert RGB)
4. **Sandbox proxy malformed IPv6** → must `unset ...proxy...` before running, otherwise HTTP library crashes
5. **`op read` with spaces/parentheses in title fails** → always use item ID
6. **Skill base64 corruption** → verify decode consistency when regenerating

---

## ✨ Final Solution

### Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  User uploads │ ──▶ │   Claude Agent    │ ──▶ │ Doubao vision    │
│ (uploads dir) │     │ (no native vision)│     │ 2.1-pro (Ark API)│
└─────────────┘     └──────────────────┘     └──────────────────┘
                           │  ▲
                           ▼  │
                    ┌──────────────────┐
                    │ 1Password key    │
                    │ (op CLI auto)     │
                    └──────────────────┘
```

### Core Capabilities

| Capability | Description |
|------------|-------------|
| 🖼️ **5 recognition modes** | UI reproduction / problem location / log extraction / OCR / general description |
| 🔄 **Image comparison** | Find real differences, guard against hallucination |
| 📦 **Auto-downscale** | >2048px auto-resize, avoids oversized API requests |
| 🔑 **Auto key fetch** | env var → 1Password op → clear error; never hardcoded |
| 🚀 **Dual model** | quality-first (deep thinking) + batch speed (low latency) |
| 🪶 **Zero third-party deps** | Pure Python stdlib + Pillow |

### Tech Stack

- **Vision model**: Doubao Seed 2.1 Pro (`doubao-seed-2-1-pro-260628`) / 2.0 Mini
- **API**: Volcano Engine Ark (OpenAI-compatible)
- **Credentials**: 1Password CLI (`op`) + Service Account token
- **Language**: Python 3.8+ (urllib + Pillow)

---

## 🚀 Quick Start

### 1. Install dependency

```bash
pip install Pillow
```

### 2. Configure API Key (either)

```bash
# Option 1: environment variable
export ARK_API_KEY="ark-..."

# Option 2: 1Password (recommended)
# op read "op://Claude Code/Ark API Key (豆包视觉)/credential"
```

### 3. Analyze your first image

```bash
python3 vision_doubao.py your_image.png E "Describe this image"
```

---

## 📖 User Guide

### Mode Reference

| Mode | Purpose | Example |
|------|---------|---------|
| `A` | **UI pixel reproduction**: layout/coords/colors/fonts | `vision_doubao.py ui.png A "Reproduce page"` |
| `B` | **Problem location**: UI bugs/misalignment/overlap | `vision_doubao.py bug.png B` |
| `C` | **Error log extraction**: verbatim errors/stacks | `vision_doubao.py error.png C` |
| `D` | **OCR**: verbatim text extraction | `vision_doubao.py doc.png D` |
| `E` | **General description**: objects/scenes/photos | `vision_doubao.py photo.jpg E` |
| `compare` | **Image comparison**: find real differences | `vision_doubao.py compare a.png b.png` |

### Model Switching

```bash
# Quality-first (default)
python3 vision_doubao.py img.png E

# Batch speed
python3 vision_doubao.py img.png D --model doubao-seed-2-0-mini-260428

# Environment variable
export ARK_MODEL="doubao-seed-2-0-mini-260428"
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARK_API_KEY` | — | Volcano Engine Ark key (highest priority) |
| `ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3/chat/completions` | API endpoint |
| `ARK_MODEL` | `doubao-seed-2-1-pro-260628` | Default model |
| `OP_REF` | `op://Claude Code/Ark API Key (豆包视觉)/credential` | 1Password reference |

---

## 🔁 Automation Workflow

### UI Pixel Reproduction Loop

```
Design → Doubao vision A analysis → write HTML/CSS → screenshot → compare image comparison → fix → aligned
```

### Auto-Analyze on Upload

Once configured with Claude memory rules, **user uploads an image → Agent analyzes automatically**, no manual trigger needed:
- Auto-find uploads directory
- Auto-select mode (default E when unsure)
- Auto-downscale / convert format
- Results presented directly

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Big image timeout | Downscale to 1280px first |
| webp rejected | Convert to JPEG |
| Proxy error `Invalid port` | `unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy NO_PROXY no_proxy` |
| 401 key invalid | Check Volcano Engine console key/balance |
| 429 rate limited | Retry later |
| 403 no permission | Switch model |

---

## 📚 References

See [REFERENCES.md](REFERENCES.md) for all models, platforms, dependencies, and their licenses.

- **Vision models**: [Doubao Seed (Volcano Engine Ark)](https://www.volcengine.com/product/ark)
- **API platform**: [Volcano Engine](https://www.volcengine.com/) · [Ark Docs](https://www.volcengine.com/docs/82379)
- **Credentials**: [1Password Developer](https://developer.1password.com/)
- **Dependencies**: [Pillow](https://python-pillow.org/) · [Python](https://www.python.org/)

---

## 🤝 Credits

Born from a real pain point — "the model can't see images" — refined through multiple iterations. Thanks to Doubao Seed for powerful vision understanding, and 1Password for secure credential management.

---

## 📄 License

MIT — see [LICENSE](LICENSE). Free to use, modify, and share.

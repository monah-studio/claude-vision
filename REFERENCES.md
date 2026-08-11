# References — Models, Platforms & Dependencies

All tools, models, and platforms referenced by this project, with official links and license information.

## Vision Models (豆包 / Doubao Seed)

| Name | Provider | License / Access | Official Link |
|------|----------|-----------------|---------------|
| **Doubao Seed 2.1 Pro** (`doubao-seed-2-1-pro-260628`) | ByteDance / Volcano Engine | Commercial API (pay-per-token) | [Volcano Engine Ark](https://www.volcengine.com/product/ark) · [Docs](https://www.volcengine.com/docs/82379) |
| **Doubao Seed 2.0 Mini** (`doubao-seed-2-0-mini-260428`) | ByteDance / Volcano Engine | Commercial API (pay-per-token) | [Volcano Engine Ark](https://www.volcengine.com/product/ark) |
| Doubao Seed 1.6 Vision (legacy fallback) | ByteDance / Volcano Engine | Commercial API | [Model Studio](https://www.volcengine.com/docs/82379/1302008) |

## API Platform

| Name | Description | License | Official Link |
|------|-------------|---------|---------------|
| **Volcano Engine Ark** (火山方舟) | LLM/vision API platform, OpenAI-compatible endpoint | Commercial | [Volcano Engine](https://www.volcengine.com/) · [Ark API Docs](https://www.volcengine.com/docs/82379/1298454) · [API Key Management](https://console.volcengine.com/ark) |
| **DashScope** (阿里云百炼) | Alternative vision API (Qwen), used in earlier versions | Commercial | [Aliyun Model Studio](https://dashscope.aliyun.com/) |
| **Qwen3-VL-Flash** | Qwen vision model (earlier version, replaced by Doubao) | Commercial API | [Qwen Docs](https://help.aliyun.com/zh/model-studio/vision) |

## Credential Management

| Name | Description | License | Official Link |
|------|-------------|---------|---------------|
| **1Password CLI** (`op`) | Secrets management, service-account token auth | Commercial (proprietary) | [1Password](https://1password.com/) · [Developer Docs](https://developer.1password.com/) · [op CLI](https://developer.1password.com/docs/cli/) |
| **1Password Service Accounts** | Server-to-server auth for 1Password | Commercial | [Service Accounts Docs](https://developer.1password.com/docs/service-accounts/) |

## Software Dependencies

| Name | Description | License | Official Link |
|------|-------------|---------|---------------|
| **Python 3.8+** | Runtime | PSF License | [python.org](https://www.python.org/) |
| **Pillow** (PIL) | Image processing | HPND License (MIT-style) | [Pillow Docs](https://python-pillow.org/) · [PyPI](https://pypi.org/project/Pillow/) |
| **Git** | Version control | GPL-2.0 | [git-scm.com](https://git-scm.com/) |
| **urllib** (stdlib) | HTTP client (no third-party dependency) | PSF License | [Python Docs](https://docs.python.org/3/library/urllib.request.html) |

## Claude (this project is built by/for Claude)

| Name | Description | License | Official Link |
|------|-------------|---------|---------------|
| **Claude Desktop App** | Environment running this agent | Commercial | [Claude](https://claude.com/) |
| **Claude Code** | CLI tool for Claude | Commercial | [Anthropic Docs](https://docs.anthropic.com/en/docs/claude-code) |
| **Anthropic API** | Claude model API | Commercial | [Anthropic](https://www.anthropic.com/) · [API Docs](https://docs.anthropic.com/) |

## Project License

This project itself is licensed under the **MIT License** — see [LICENSE](LICENSE).

> **Note**: The vision models and API platforms listed above are commercial services. Using them requires your own account and API keys. This project only provides the client-side script; it does not bundle or redistribute the models.

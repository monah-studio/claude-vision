#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vision_doubao.py — 用豆包视觉模型（火山方舟 Ark）帮 Claude 看图
用法：
  python3 vision_doubao.py <图> A "额外指令"        # UI 页面还原
  python3 vision_doubao.py <图> B                  # 问题定位
  python3 vision_doubao.py <图> C                  # 错误日志/堆栈提取
  python3 vision_doubao.py <图> D                  # OCR 文字提取
  python3 vision_doubao.py <图> E "额外指令"        # 通用描述
  python3 vision_doubao.py compare <图1> <图2> "指令" # 双图对比
Key 获取优先级：ARK_API_KEY 环境变量 > 1Password op CLI（引用可用 OP_REF 配置）> 报错。
不硬编码密钥。
模型：默认 doubao-seed-2-1-pro-260628（质量优先，深度思考）
      批量/跑量：--model doubao-seed-2-0-mini-260428（低时延高并发）
      优先级：--model 参数 > ARK_MODEL 环境变量 > 默认 2-1-pro
"""
import sys, os, io, base64, json, urllib.request, urllib.error

ENDPOINT = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
# 模型：doubao-seed-2-0-mini-260428（全模态，社区实测）; 备选 doubao-seed-1-6-vision
DEFAULT_MODEL = "doubao-seed-2-1-pro-260628"
MODEL = os.environ.get("ARK_MODEL", DEFAULT_MODEL)
MAX_EDGE = 2048
TIMEOUT = 150

PROMPTS = {
    "A": (
        "你正在做 UI 像素级还原。请把这张图的界面完整拆解出来，输出如下：\n"
        "1) 整体布局：用 ASCII 示意图表示各区域（顶部/导航/内容/底部），标出尺寸或比例；\n"
        "2) 每个区块的：区块名、坐标(x,y)、宽高(px)、内边距、间距；\n"
        "3) 颜色体系：用到的颜色及对应 hex 值\n"
        "4) 字体与字号：字体族、字号层级\n"
        "5) 交互状态与特殊元素\n"
        "如果图中含有文字，逐字提取并按位置归入对应区块。数值请尽量精确，不确定的标注'约'。"
    ),
    "B": (
        "你正在做问题定位。请仔细看这张图，列出图中最可能的问题，包括：\n"
        "1) 各元素的位置关系（坐标/对齐/间距）；\n"
        "2) 明显异常或错位的地方（重叠/缺失/变形）；\n"
        "3) 可能的原因判断；\n"
        "4) 修复建议。\n"
        "如有具体坐标或尺寸请给出，不确定的标注'约'。不要臆造图中不存在的差异。"
    ),
    "C": (
        "你正在做错误分析。请把图中出现的报错信息、日志或堆栈逐字提取出来，包括：\n"
        "不要概括、不要翻译，保持原文；\n"
        "不要补充图中没有的信息。\n"
        "若图中有明显的错误/异常信息，用列表逐条列出。"
    ),
    "D": (
        "你正在做 OCR 文字提取。请把图中所有文字逐字提取出来，包括标题、正文、按钮、标签、数字；\n"
        "尽量保持原文、保留换行；\n"
        "不要翻译、不要概括；\n"
        "若图中没有文字，直接说明'图中无文字'。\n"
        "如排版适合用 Markdown 表格呈现，可以直接输出表格。"
    ),
    "E": (
        "请详细描述这张图：主体与背景、内容要点、文字与视觉元素。\n"
        "若为实物/硬件照片，请描述外观、接口、标识、按键、品牌信息等；\n"
        "若有文字请一并提取。\n"
    )
}

def encode_image(path):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("缺少 Pillow: 请运行  pip install --break-system-packages pillow")
    with Image.open(path) as im:
        im.load()
        desc = f"{path} ({im.format} {im.size[0]}x{im.size[1]}, {im.mode})"
        if max(im.size) > MAX_EDGE:
            scale = MAX_EDGE / max(im.size)
            new = (int(im.size[0]*scale), int(im.size[1]*scale))
            im = im.resize(new, Image.LANCZOS)
            desc += f" → 已缩放到 {new[0]}x{new[1]}"
        buf = io.BytesIO()
        if im.format == "PNG":
            im.save(buf, format="PNG")
        else:
            im = im.convert("RGB")
            im.save(buf, format="JPEG", quality=88)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64, desc

def call_api(api_key, messages):
    payload = json.dumps({"model": MODEL, "messages": messages, "max_tokens": 4096}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(body)
            msg = err.get("error", {}).get("message", body)
        except Exception:
            msg = body
        return f"[API 错误 {e.code}] {msg}"
    except Exception as e:
        return f"[请求失败] {e}"

VALID_MODELS = {
    "doubao-seed-2-1-pro-260628": "质量优先（深度思考）",
    "doubao-seed-2-0-mini-260428": "批量/跑量（低时延）",
    "doubao-seed-1-6-vision": "旧视觉专用（备用）",
}

def parse_model(argv):
    """--model <id> 从 argv 里提取并移除。优先级: --model > env > default。"""
    global MODEL
    if "--model" in argv:
        i = argv.index("--model")
        if i + 1 < len(argv):
            m = argv[i + 1]
            if m in VALID_MODELS:
                MODEL = m
                del argv[i:i + 2]
            else:
                sys.exit(f"未知模型: {m}。可用: {', '.join(VALID_MODELS)}")
    return argv

def content_block(b64):
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}

# 1Password 中存储豆包视觉 key 的引用。可通过 OP_REF 环境变量覆盖。
OP_REF = os.environ.get("OP_REF", "op://Claude Code/5jihua4nve4oila2zzumwwmfgi/credential")

def resolve_api_key():
    """取 key：环境变量 ARK_API_KEY > 1Password op CLI (OP_REF) > 报错。"""
    key = os.environ.get("ARK_API_KEY", "").strip()
    if key:
        return key
    import subprocess
    try:
        env = {k: v for k, v in os.environ.items()
               if k not in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                            "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy")}
        r = subprocess.run(["op", "read", OP_REF],
                           capture_output=True, text=True, timeout=15, env=env)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    sys.exit("缺少 ARK_API_KEY：无法从环境变量或 1Password 取到火山方舟 key。\n"
             "设置环境变量 ARK_API_KEY，或配置 op CLI（1Password 条目引用可用 OP_REF 指定）。")

def main(argv):
    argv = parse_model(list(argv))
    api_key = resolve_api_key()

    if len(argv) >= 3 and argv[0] == "compare":
        b1, d1 = encode_image(argv[1])
        b2, d2 = encode_image(argv[2])
        extra = " ".join(argv[3:])
        prompt = ("请对比这两张图，找出它们之间真实存在的差异。"
                  "只描述你确实看到的差异，并给出图中证据位置；"
                  "不要臆造不存在的差异。") + (f"\n关注点：{extra}" if extra else "")
        msg = {"role": "user", "content": [content_block(b1), content_block(b2), {"type": "text", "text": prompt}]}
        print(f"# 图1: {d1}\n# 图2: {d2}")
        print(call_api(api_key, [msg]))
        return

    img = argv[0]
    mode = argv[1].upper() if len(argv) > 1 else "E"
    extra = " ".join(argv[2:])
    prompt = PROMPTS.get(mode, PROMPTS["E"]) + (f"\n额外指令：{extra}" if extra else "")
    b64, desc = encode_image(img)
    print(f"# {desc}  |  模型 {MODEL} ({VALID_MODELS.get(MODEL, MODEL)})")
    msg = {"role": "user", "content": [content_block(b64), {"type": "text", "text": prompt}]}
    print(call_api(api_key, [msg]))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vision_deepseek.py — 帮 Claude 看图（DeepSeek V4 Flash Vision，唯一模型）

用法：
  python3 vision_deepseek.py <图> E "额外指令"            # 通用描述（A/B/C/D/E/S 模式）
  python3 vision_deepseek.py <图1> <图2> E "指令"          # 多图一次分析（按顺序逐张）
  python3 vision_deepseek.py compare <图1> <图2> "指令"    # 双图对比
  python3 vision_deepseek.py recent [n] [模式] [指令]      # 自动从会话记录恢复最近 n 张图并分析（默认最新，分析完自动清理）
  python3 vision_deepseek.py list [n]                     # 只列出可恢复的图片，不分析

模式：A=UI 像素还原  B=问题定位  C=错误/日志提取  D=OCR  E=通用描述  S=一句话概括（最省 context）
通用参数：--out FILE（把完整结果写到文件，终端只回一行确认，省 context）

模型：deepseek-v4-flash-vision-exp（实验版，图片转 token 计费，一张图最多 384 tokens）
Key 优先级：DEEPSEEK_API_KEY 环境变量 > 内置默认 key > 1Password op CLI > 报错。
环境变量可调：VISION_MODEL / VISION_ENDPOINT / VISION_MAX_EDGE / VISION_WEBP_QUALITY / VISION_TIMEOUT / VISION_STREAM(0 关)
特性：流式输出 + 429/5xx/超时自动重试 + EXIF 方向纠正 + 透明图白底 + 小图直传 + BILINEAR/WebP 压缩。
不硬编码密钥到仓库（GitHub 版本内置 key 留空）。
"""
import sys, os, io, re, glob, time, base64, json, urllib.request, urllib.error

MODEL = os.environ.get("VISION_MODEL", "deepseek-v4-flash-vision-exp")
ENDPOINT = os.environ.get("VISION_ENDPOINT", "https://api.deepseek.com/chat/completions")
# 内置默认 key（本地版用；GitHub 版留空）。优先级低于环境变量 DEEPSEEK_API_KEY。
DEFAULT_API_KEY = ""
MAX_EDGE = int(os.environ.get("VISION_MAX_EDGE", "1280"))   # 压缩到长边 1280，避免大图撑爆上下文
MAX_RAW_BYTES = 512 * 1024  # 小图（≤512KB）直接传原字节，跳过解码/重编码
WEBP_QUALITY = int(os.environ.get("VISION_WEBP_QUALITY", "72"))  # WebP 主压缩（比 JPEG 小约 10 倍）
JPEG_QUALITY = 82  # WebP 不可用时回退 JPEG
TIMEOUT = int(os.environ.get("VISION_TIMEOUT", "150"))
RETRIES = 3
STREAM = os.environ.get("VISION_STREAM", "1") != "0"

# 按模式限制最大输出 token（加速：短模式不用生成 4096 字）
MODE_MAX_TOKENS = {"S": 400, "D": 1200, "C": 1200, "B": 2000, "A": 3000, "E": 4096}
# 按模式限制图片长边（S 模式用更小图 → 更少图片 token → 首字更快）
MODE_MAX_EDGE = {"S": 768}

# 会话记录目录（恢复粘贴图片用）：多个会话各自的 JSONL 都在这里
PROJECTS_GLOB = "/sessions/*/mnt/.claude/projects/**/*.jsonl"
RECOVER_DIR = "/tmp/recovered"
MEDIA_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg",
             "image/webp": "webp", "image/gif": "gif", "image/bmp": "bmp"}

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
    ),
    "S": (
        "用不超过 3 句话概括这张图的核心内容：它是什么、关键文字或数字、最重要的视觉信息。"
        "只输出结论，不要分节、不要标题、不要展开。"
    ),
}


def encode_image(path, max_edge=None):
    max_edge = max_edge or MAX_EDGE
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("缺少 Pillow: 请运行  pip install --break-system-packages pillow")
    MIME = {"WEBP": "image/webp", "JPEG": "image/jpeg", "PNG": "image/png", "GIF": "image/gif"}
    with open(path, "rb") as f:
        raw = f.read()
    with Image.open(path) as im:  # 只读头部，不完整解码
        w, h = im.size
        fmt = im.format or ""
    desc = f"{path} ({fmt} {w}x{h})"
    # 快速路径：已是小图（≤1280 且 ≤512KB），直接传原字节，跳过解码/缩放/重编码
    if fmt in MIME and max(w, h) <= max_edge and len(raw) <= MAX_RAW_BYTES:
        return base64.b64encode(raw).decode("ascii"), desc, MIME[fmt]
    # 慢路径：EXIF 纠方向 → 大图缩放（BILINEAR 快约 4 倍）→ 透明图垫白底 → WebP method 0 压缩
    with Image.open(path) as im:
        try:
            im = ImageOps.exif_transpose(im)   # 手机照片按 EXIF 方向摆正
        except Exception:
            pass
        im.load()
        if max(im.size) > max_edge:
            scale = max_edge / max(im.size)
            new = (int(im.size[0] * scale), int(im.size[1] * scale))
            im = im.resize(new, Image.BILINEAR)
            desc += f" → 已缩放到 {new[0]}x{new[1]}"
        # 透明图（RGBA/LA/P 带透明）垫白底，避免转 RGB 后变黑
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[3])
            im = bg
        else:
            im = im.convert("RGB")
        buf = io.BytesIO()
        try:
            im.save(buf, format="WEBP", quality=WEBP_QUALITY, method=0)
            mime = "image/webp"
        except Exception:
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            mime = "image/jpeg"
    return base64.b64encode(buf.getvalue()).decode("ascii"), desc, mime


class ApiError(Exception):
    def __init__(self, msg, retryable=False):
        super().__init__(msg)
        self.retryable = retryable


def _extract_err(body):
    try:
        return json.loads(body).get("error", {}).get("message", body)
    except Exception:
        return body


def call_api(api_key, messages, stream=True, max_tokens=4096):
    """调用 DeepSeek；stream=True 时边生成边打印，返回完整文本。
    出错抛 ApiError（retryable=True 表示可重试）。"""
    payload = json.dumps({"model": MODEL, "messages": messages, "max_tokens": max_tokens,
                          "thinking": {"type": "disabled"}, "stream": stream}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        retryable = e.code in (429, 500, 502, 503, 504)
        raise ApiError(f"[API 错误 {e.code}] {_extract_err(body)}", retryable)
    except Exception as e:
        raise ApiError(f"[请求失败] {e}", True)

    if not stream:
        try:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        finally:
            resp.close()

    buf = []
    try:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                delta = json.loads(chunk)["choices"][0].get("delta", {}).get("content")
                if delta:
                    sys.stdout.write(delta)
                    sys.stdout.flush()
                    buf.append(delta)
            except Exception:
                continue
    except Exception as e:
        raise ApiError(f"[流式读取失败] {e}", True)
    finally:
        resp.close()
    sys.stdout.write("\n")
    sys.stdout.flush()
    return "".join(buf)


def call_with_retry(api_key, messages, stream=True, max_tokens=4096):
    last = None
    for i in range(RETRIES):
        try:
            return call_api(api_key, messages, stream=stream, max_tokens=max_tokens)
        except ApiError as e:
            last = str(e)
            if not e.retryable or i == RETRIES - 1:
                break
            time.sleep(1 + i)
    # 流式失败 → 兜底走非流式一次
    try:
        return call_api(api_key, messages, stream=False, max_tokens=max_tokens)
    except ApiError as e:
        return last or str(e)


def content_block(b64, mime="image/jpeg"):
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def resolve_api_key():
    """取 key：环境变量 DEEPSEEK_API_KEY > 内置默认 > 1Password op CLI > 报错。"""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    if DEFAULT_API_KEY:
        return DEFAULT_API_KEY
    import subprocess
    try:
        env = {k: v for k, v in os.environ.items()
               if k not in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                            "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy")}
        r = subprocess.run(["op", "read", "op://Claude Code/putw5bqgdxoqapulcit5qmszge/credential"],
                           capture_output=True, text=True, timeout=15, env=env)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    sys.exit("缺少 DEEPSEEK_API_KEY：无法从环境变量、内置默认或 1Password 取到 DeepSeek key。\n"
             "设置环境变量 DEEPSEEK_API_KEY，或更新 1Password 条目 putw5bqgdxoqapulcit5qmszge。")


# ---------------------------------------------------------------------------
# 图片恢复（从会话 JSONL 提取粘贴图）——内联版，去掉对 recover_image.py 的依赖
# ---------------------------------------------------------------------------
def _extract_imgs(content, out):
    if isinstance(content, dict):
        t = content.get("type")
        if t == "image":
            src = content.get("source", {})
            if isinstance(src, dict) and src.get("data"):
                out.append((src.get("media_type", "image/png"), src["data"]))
        elif t == "image_url":
            url = (content.get("image_url") or {}).get("url", "")
            m = re.match(r"data:([^;]+);base64,(.+)", url or "", re.S)
            if m:
                out.append((m.group(1), m.group(2)))
        for v in content.values():
            _extract_imgs(v, out)
    elif isinstance(content, list):
        for v in content:
            _extract_imgs(v, out)


def recover_images(limit=0):
    """扫描会话 JSONL，恢复粘贴图到 /tmp/recovered，返回列表（旧→新）。"""
    files = [f for f in glob.glob(PROJECTS_GLOB, recursive=True) if os.path.isfile(f)]
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    os.makedirs(RECOVER_DIR, exist_ok=True)
    found = []
    for jl in files:
        try:
            fh = open(jl, encoding="utf-8", errors="replace")
        except Exception:
            continue
        try:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "user":
                    continue
                imgs = []
                _extract_imgs(obj.get("message", {}).get("content"), imgs)
                for media, data in imgs:
                    try:
                        raw = base64.b64decode(data)
                    except Exception:
                        continue
                    ext = MEDIA_EXT.get(media.split(";")[0], "png")
                    fn = os.path.join(RECOVER_DIR, f"img_{len(found) + 1:03d}.{ext}")
                    with open(fn, "wb") as w:
                        w.write(raw)
                    found.append({"path": fn, "media_type": media, "size": len(raw)})
                    if limit and len(found) >= limit:
                        return found
        finally:
            fh.close()
    return found


def cleanup_recovered():
    for f in glob.glob(os.path.join(RECOVER_DIR, "*")):
        try:
            os.remove(f)
        except Exception:
            pass


def _split_out(rest):
    """从额外参数里剥离 --out FILE；返回 (剩余参数, out_path)。"""
    out_path = None
    cleaned = []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--out" and i + 1 < len(rest):
            out_path = rest[i + 1]
            i += 2
            continue
        if a.startswith("--out="):
            out_path = a.split("=", 1)[1]
            i += 1
            continue
        cleaned.append(a)
        i += 1
    return cleaned, out_path


def parse_mode_extra(rest):
    rest, out_path = _split_out(rest)
    if rest and rest[0].upper() in PROMPTS:
        return rest[0].upper(), " ".join(rest[1:]), out_path
    return "E", " ".join(rest), out_path


def emit(text, out_path, streamed=False):
    """输出结果：指定 --out 则写文件、终端只回一行确认；否则（未流式时）打印全文。"""
    if out_path:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[已写入 {out_path}，{len(text)} 字]")
            return
        except Exception as e:
            print(f"[写入文件失败] {e}")
    if not streamed:
        print(text)


def analyze_paths(api_key, images, mode, extra, out_path):
    """把一组图片路径拼成一个请求并分析。返回 (文本, 是否已流式打印)。"""
    stream = STREAM and not out_path
    mt = MODE_MAX_TOKENS.get(mode, 4096)   # 按模式限制最大输出，短模式更快
    me = MODE_MAX_EDGE.get(mode, MAX_EDGE)  # S 模式用更小图，首字更快
    if len(images) == 1:
        prompt = PROMPTS.get(mode, PROMPTS["E"]) + (f"\n额外指令：{extra}" if extra else "")
        b64, desc, mime = encode_image(images[0], max_edge=me)
        print(f"# {desc}  |  模型 {MODEL}")
        msg = {"role": "user", "content": [content_block(b64, mime), {"type": "text", "text": prompt}]}
        t0 = time.time()
        res = call_with_retry(api_key, [msg], stream=stream, max_tokens=mt)
        print(f"[耗时 {time.time() - t0:.2f}s]")
        return res, stream

    blocks, descs = [], []
    for p in images:
        b64, desc, mime = encode_image(p, max_edge=me)
        blocks.append(content_block(b64, mime))
        descs.append(desc)
    prompt = (f"这是 {len(images)} 张图片。请按顺序逐张分析，每张用「图 1 / 图 2 …」标注，"
              f"并指出它们之间的关联或差异（如有）。") + (f"\n额外指令：{extra}" if extra else "")
    print("# " + "  ".join(descs) + f"  |  模型 {MODEL}")
    msg = {"role": "user", "content": blocks + [{"type": "text", "text": prompt}]}
    t0 = time.time()
    res = call_with_retry(api_key, [msg], stream=stream, max_tokens=mt)
    print(f"[耗时 {time.time() - t0:.2f}s]")
    return res, stream


def main(argv):
    if not argv:
        print(__doc__)
        return 0

    # ---- 子命令：list（只列不分析）----
    if argv[0] == "list":
        n = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 0
        imgs = recover_images(n)
        print(json.dumps(imgs, ensure_ascii=False, indent=2))
        return 0

    api_key = resolve_api_key()

    # ---- 子命令：recent（自动恢复最近 n 张图 → 分析 → 清理）----
    if argv[0] == "recent":
        rest = argv[1:]
        n = 1
        if rest and rest[0].isdigit():
            n = int(rest[0])
            rest = rest[1:]
        n = max(1, n)
        imgs = recover_images()
        if not imgs:
            print("[recover] 未在会话记录中找到可分析的图片")
            return 1
        n = min(n, len(imgs))
        images = [imgs[-n]["path"]] if n == 1 else [im["path"] for im in imgs[-n:]]
        mode, extra, out_path = parse_mode_extra(rest)
        out, streamed = analyze_paths(api_key, images, mode, extra, out_path)
        emit(out, out_path, streamed)
        cleanup_recovered()   # 分析完自动删除，不占 context
        return 0 if not out.startswith("[") else 1

    # ---- 子命令：compare（双图对比）----
    if len(argv) >= 3 and argv[0] == "compare":
        rest, out_path = _split_out(argv[3:])
        b1, d1, m1 = encode_image(argv[1])
        b2, d2, m2 = encode_image(argv[2])
        extra = " ".join(rest)
        prompt = ("请对比这两张图，找出它们之间真实存在的差异。"
                  "只描述你确实看到的差异，并给出图中证据位置；"
                  "不要臆造不存在的差异。") + (f"\n关注点：{extra}" if extra else "")
        msg = {"role": "user", "content": [
            content_block(b1, m1), content_block(b2, m2), {"type": "text", "text": prompt}]}
        print(f"# 图1: {d1}\n# 图2: {d2}")
        streamed = STREAM and not out_path
        t0 = time.time()
        res = call_with_retry(api_key, [msg], stream=streamed)
        emit(res, out_path, streamed)
        print(f"[耗时 {time.time() - t0:.2f}s]")
        return 0

    # ---- 普通路径：把 argv 里存在的文件路径收集为图片，其余当作模式/指令 ----
    images = []
    i = 0
    while i < len(argv) and os.path.isfile(argv[i]):
        images.append(argv[i])
        i += 1
    if not images:
        print("[error] 未提供图片路径（文件不存在）。可先跑  recent  /  list  找图。")
        return 1
    mode, extra, out_path = parse_mode_extra(argv[i:])
    out, streamed = analyze_paths(api_key, images, mode, extra, out_path)
    emit(out, out_path, streamed)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))

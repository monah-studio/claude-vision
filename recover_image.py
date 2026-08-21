#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recover_image.py — 从 Claude Code 会话记录(JSONL)恢复粘贴的图片

背景：模型无内置看图能力时，用户粘贴的图片在上下文里显示 [Unsupported Image]，
但图片字节仍完整存在本地会话 JSONL 的 user 消息 content 里。本脚本把它们提取成文件。

用法：
  python3 recover_image.py                     # 扫最近会话，恢复全部图片到 /tmp/recovered
  python3 recover_image.py --count 1           # 只恢复最近 1 张
  python3 recover_image.py --out /tmp/rec      # 指定输出目录
  python3 recover_image.py --jsonl <path>      # 指定某个 JSONL 文件

输出：JSON 数组（旧→新），每项含 path / media_type / size / line / session。
"""
import sys, os, json, base64, re, glob, argparse

# 会话记录目录：多个会话各自的 JSONL 都在这里（按 cwd 编码分子目录）
PROJECTS_GLOB = "/sessions/*/mnt/.claude/projects/**/*.jsonl"

MEDIA_EXT = {
    "image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg",
    "image/webp": "webp", "image/gif": "gif", "image/bmp": "bmp",
}

def find_jsonl():
    files = [f for f in glob.glob(PROJECTS_GLOB, recursive=True) if os.path.isfile(f)]
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)  # 最近改动的优先
    return files

def extract_images(content, results):
    """递归提取 content 里的 base64 图片。支持两种形态：
    - {"type":"image","source":{"type":"base64","media_type":"image/webp","data":"..."}}
    - {"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}
    """
    if isinstance(content, dict):
        t = content.get("type")
        if t == "image":
            src = content.get("source", {})
            if isinstance(src, dict) and src.get("data"):
                results.append((src.get("media_type", "image/png"), src["data"]))
        elif t == "image_url":
            url = (content.get("image_url") or {}).get("url", "")
            m = re.match(r"data:([^;]+);base64,(.+)", url or "", re.S)
            if m:
                results.append((m.group(1), m.group(2)))
        for v in content.values():
            extract_images(v, results)
    elif isinstance(content, list):
        for v in content:
            extract_images(v, results)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/recovered")
    ap.add_argument("--count", type=int, default=0, help="最多恢复几张（0=全部）")
    ap.add_argument("--jsonl", default="", help="指定 JSONL 文件，跳过自动探测")
    args = ap.parse_args()

    files = [args.jsonl] if args.jsonl else find_jsonl()
    os.makedirs(args.out, exist_ok=True)

    found = []
    for jl in files:
        if not os.path.isfile(jl):
            continue
        try:
            fh = open(jl, encoding="utf-8", errors="replace")
        except Exception:
            continue
        try:
            for ln, line in enumerate(fh, 1):
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
                extract_images(obj.get("message", {}).get("content"), imgs)
                for media, data in imgs:
                    try:
                        raw = base64.b64decode(data)
                    except Exception:
                        continue
                    ext = MEDIA_EXT.get(media.split(";")[0], "png")
                    idx = len(found) + 1
                    fn = os.path.join(args.out, f"img_{idx:03d}.{ext}")
                    with open(fn, "wb") as w:
                        w.write(raw)
                    found.append({"path": fn, "media_type": media,
                                  "size": len(raw), "line": ln, "session": jl})
                    if args.count and len(found) >= args.count:
                        print(json.dumps(found, ensure_ascii=False, indent=2))
                        return
        finally:
            fh.close()

    print(json.dumps(found, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

#!/usr/bin/env python3
"""环境自检：看看电脑上该有的东西齐不齐。

    python check.py
"""

from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.console import pad, setup as setup_console  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))


def line(label, ok, detail=""):
    mark = "OK  " if ok else "!   "
    print("  [%s] %s%s" % (mark, pad(label, 18), detail))


def main():
    setup_console()
    print("\n饮冰室 · 环境自检")
    print("=" * 52)

    version = "%d.%d.%d" % sys.version_info[:3]
    line("Python", sys.version_info >= (3, 9), version + ("（可以用）" if sys.version_info >= (3, 9) else "（太旧，需要 3.9+）"))
    line("项目文件夹", os.path.isfile(os.path.join(ROOT, "build.py")), ROOT)

    try:
        import PIL  # noqa: F401

        line("Pillow（分享图）", True, "已安装，每篇文章会有自己的分享图")
    except ImportError:
        line("Pillow（分享图）", False, "没装也不影响网站；菜单里选 4 可以装")

    posts = glob.glob(os.path.join(ROOT, "content", "posts", "*.md"))
    posts = [p for p in posts if not os.path.basename(p).startswith(("_", "."))]
    line("文章", bool(posts), "%d 篇" % len(posts))

    public_index = os.path.join(ROOT, "public", "index.html")
    if os.path.isfile(public_index):
        pages = len(glob.glob(os.path.join(ROOT, "public", "**", "*.html"), recursive=True))
        line("已生成网站", True, "%d 个页面，可以直接预览或上传" % pages)
    else:
        line("已生成网站", False, "还没生成，选 1 或 2 生成一次")

    print("=" * 52)
    print("  一切正常的话，选 2 就能在浏览器里看到你的网站。")
    print("  有 ⚠️ 的那一项，按提示处理即可，不影响其他功能。\n")


if __name__ == "__main__":
    main()

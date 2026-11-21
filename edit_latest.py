#!/usr/bin/env python3
"""打开最近改过的那篇文章，方便继续写。

    python edit_latest.py
"""

from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.console import setup as setup_console  # noqa: E402
from new_post import open_in_editor  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(ROOT, "content", "posts")


def main():
    setup_console()
    files = [
        path
        for path in glob.glob(os.path.join(POSTS_DIR, "*.md"))
        if not os.path.basename(path).startswith(("_", "."))
    ]

    if not files:
        print("\n还没有文章。先双击桌面上的「② 写一篇新文章」。\n")
        return

    latest = max(files, key=os.path.getmtime)
    print("\n正在打开你最近写的那篇：" + os.path.basename(latest))
    print("改完按 Ctrl+S 保存，然后双击「① 预览我的网站」看效果。\n")
    open_in_editor(latest)


if __name__ == "__main__":
    main()

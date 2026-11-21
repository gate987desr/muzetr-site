#!/usr/bin/env python3
"""生成网站 → 打包成 zip → 打开 Netlify 的 Deploys 页面。

    python package.py            # 生成 + 打包
    python package.py --open     # 再打开 Netlify 上传页
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import webbrowser
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.console import setup as setup_console  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
ZIP_NAME = "muzetr网站.zip"
SITE_FOLDER = "饮冰室-网站"  # 桌面上的文件夹名，zip 会放在这里


def desktop_dir():
    home = os.path.expanduser("~")
    for candidate in (
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
    ):
        if os.path.isdir(candidate):
            return candidate
    return home


def main():
    setup_console()
    print("\n  [1/2] 正在生成网站…\n")
    if subprocess.call([sys.executable, os.path.join(ROOT, "build.py")]) != 0:
        print("\n  生成失败，先修上面报的错。")
        return

    if not os.path.isfile(os.path.join(PUBLIC, "index.html")):
        print("\n  public/ 里没有 index.html，生成似乎没成功。")
        return

    target_dir = os.path.join(desktop_dir(), SITE_FOLDER)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError:
        target_dir = desktop_dir()
    target = os.path.join(target_dir, ZIP_NAME)
    print("\n  [2/2] 正在打包成 zip…")
    temp = target + ".tmp"
    count = 0
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder, _dirs, files in os.walk(PUBLIC):
            for name in files:
                full = os.path.join(folder, name)
                archive.write(full, os.path.relpath(full, PUBLIC))
                count += 1
    os.replace(temp, target)
    size_mb = os.path.getsize(target) / 1024.0 / 1024.0

    print("  完成：%s" % target)
    print("  %.1f MB · %d 个文件" % (size_mb, count))
    print("\n  下一步：把这个 zip 拖进 Netlify 的 Deploys 页面，等它变绿就更新了。")

    site = ""
    try:
        with open(os.path.join(ROOT, "site.config.json"), encoding="utf-8") as handle:
            site = (json.load(handle).get("deploy") or {}).get("netlifySite", "")
    except Exception:  # noqa: BLE001
        site = ""

    if site:
        url = "https://app.netlify.com/sites/%s/deploys" % site
        print("  上传页：%s" % url)
        if "--open" in sys.argv:
            try:
                webbrowser.open(url)
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    main()

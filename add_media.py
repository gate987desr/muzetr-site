#!/usr/bin/env python3
"""加图片 / 视频 / 音频：选文件 → 自动放进网站 → 给你一行代码。

    python add_media.py            # 弹窗选文件
    python add_media.py 图片路径    # 直接处理
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.console import setup as setup_console  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(ROOT, "assets", "img", "posts")
MEDIA_DIR = os.path.join(ROOT, "assets", "media")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v"}
AUDIO_EXT = {".mp3", ".m4a", ".ogg", ".wav", ".flac"}


def pick_file():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="选择要加到网站上的图片 / 视频 / 音频",
            filetypes=[
                ("图片和影音", "*.jpg *.jpeg *.png *.webp *.gif *.svg *.mp4 *.webm *.mp3 *.m4a *.wav"),
                ("所有文件", "*.*"),
            ],
        )
        root.destroy()
        return path
    except Exception as exc:  # noqa: BLE001
        print("打不开选文件窗口（%s）。" % exc)
        return input("把你的文件拖到这里，然后回车： ").strip().strip('"')


def safe_stem(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    ascii_stem = re.sub(r"[^0-9A-Za-z]+", "-", stem).strip("-").lower()
    if not ascii_stem:
        ascii_stem = "media-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return ascii_stem[:48]


def unique_path(folder, stem, ext):
    os.makedirs(folder, exist_ok=True)
    candidate = os.path.join(folder, stem + ext)
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, "%s-%d%s" % (stem, counter, ext))
        counter += 1
    return candidate


def to_clipboard(text):
    if os.name != "nt":
        return False
    try:
        subprocess.run("clip", input=text.encode("gbk"), check=True, shell=True)
        return True
    except Exception:  # noqa: BLE001
        return False


def human_size(num):
    if num < 1024 * 1024:
        return "%.0f KB" % (num / 1024.0)
    return "%.1f MB" % (num / 1024.0 / 1024.0)


def main():
    setup_console()
    print("\n  饮冰室 · 加图片 / 视频 / 音频")
    print("  " + "-" * 42)

    source = sys.argv[1] if len(sys.argv) > 1 else pick_file()
    if not source:
        print("\n  没有选文件，什么都没做。\n")
        return
    source = os.path.abspath(source.strip().strip('"'))
    if not os.path.isfile(source):
        print("\n  找不到这个文件：%s\n" % source)
        return

    ext = os.path.splitext(source)[1].lower()
    size = os.path.getsize(source)
    stem = safe_stem(source)

    if ext in IMAGE_EXT:
        target = unique_path(IMG_DIR, stem, ext)
        shutil.copy2(source, target)
        rel = "/assets/img/posts/" + os.path.basename(target)
        code = "![图片说明](%s)" % rel
        kind = "图片"
        if size > 2 * 1024 * 1024:
            print("\n  提醒：这张图 %.1f MB，偏大。" % (size / 1024.0 / 1024.0))
            print("  建议压到 1 MB 以内（手机照片先用微信发给自己再保存，或去 squoosh.app 压）。")
    elif ext in VIDEO_EXT:
        target = unique_path(MEDIA_DIR, stem, ext)
        shutil.copy2(source, target)
        rel = "/assets/media/" + os.path.basename(target)
        code = '<video controls preload="metadata" src="%s"></video>' % rel
        kind = "视频"
        if size > 20 * 1024 * 1024:
            print("\n  提醒：这个视频 %.0f MB，太大了。" % (size / 1024.0 / 1024.0))
            print("  建议先传到 B 站，再用 <iframe> 贴进来（下面会给你另一种写法）。")
    elif ext in AUDIO_EXT:
        target = unique_path(MEDIA_DIR, stem, ext)
        shutil.copy2(source, target)
        rel = "/assets/media/" + os.path.basename(target)
        code = '<audio controls src="%s"></audio>' % rel
        kind = "音频"
    else:
        print("\n  这个类型（%s）还不支持。支持：jpg png webp gif svg mp4 webm mp3 m4a wav\n" % ext)
        return

    copied = to_clipboard(code)

    print("\n  ✅ %s已放进网站（%s）" % (kind, human_size(size)))
    print("  文件：%s" % os.path.relpath(target, ROOT))
    print("\n  把下面这一行，粘贴到你的文章里想显示的位置：\n")
    print("  " + code)
    print()
    if copied:
        print("  （已经复制到剪贴板，直接 Ctrl+V 就行）")
    print("  然后双击桌面「⑤ 更新到网站」，把 zip 拖上去，就出现在线上了。\n")
    if ext in VIDEO_EXT:
        print("  想要 B 站播放器（更省流量、国内更快）：")
        print('  <iframe src="//player.bilibili.com/player.html?bvid=BV号&autoplay=0" allowfullscreen></iframe>\n')


if __name__ == "__main__":
    main()

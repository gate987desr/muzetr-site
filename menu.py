#!/usr/bin/env python3
"""饮冰室 · 控制台（双击 0-开始.cmd 就会看到这个）。

所有中文界面都在 Python 里，避免批处理文件的中文乱码问题。
"""

from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.console import pad, setup as setup_console  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))

MENU = [
    ("1", "生成网站", "改完内容后点这个"),
    ("2", "本地预览", "生成并用浏览器打开"),
    ("3", "写一篇新文章", "向导式，自动填好格式"),
    ("4", "安装分享图组件", "可选，装一次就够"),
    ("5", "打开项目文件夹", "在资源管理器里查看"),
    ("6", "检查环境", "看看该有的东西齐不齐"),
    ("0", "退出", ""),
]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="\n  按回车返回菜单…"):
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        pass


def run(*args):
    try:
        return subprocess.call(list(args), cwd=ROOT)
    except KeyboardInterrupt:
        return 130


def show_menu():
    clear()
    print()
    print("   =================================================")
    print("       饮冰室 · 控制台")
    print("   =================================================")
    print()
    for key, title, note in MENU:
        print("     %s   %s%s" % (key, pad(title, 22), note))
    print()


def action_build():
    clear()
    print("\n   [1] 正在生成网站…\n")
    code = run(sys.executable, "build.py")
    print()
    if code == 0:
        print("   --------------------------------------------------")
        print("   成功。想看效果，回菜单选 2。")
    else:
        print("   生成失败了，把上面的报错整段发给我。")
    pause()


def action_preview():
    clear()
    print("\n   [2] 先生成，再打开预览…\n")
    if run(sys.executable, "build.py") != 0:
        print("\n   生成失败，先修上面的报错。")
        pause()
        return
    print("\n   正在启动本地服务器，浏览器会自动打开。")
    print("   看完回到这个窗口按 Ctrl+C 就停止。\n")
    run(sys.executable, "serve.py")
    pause()


def action_new_post():
    clear()
    run(sys.executable, "new_post.py")
    pause()


def action_pillow():
    clear()
    print("\n   [4] 正在安装 Pillow（给每篇文章生成分享图）…")
    print("   需要联网，大约十几秒。\n")
    code = run(sys.executable, "-m", "pip", "install", "pillow")
    print()
    if code == 0:
        print("   装好了。以后生成网站时，会顺便生成分享图。")
    else:
        print("   没装上也不要紧，网站照样能用。多半是网络问题，稍后再试。")
    pause()


def action_folder():
    try:
        if os.name == "nt":
            os.startfile(ROOT)  # type: ignore[attr-defined]
        else:
            print(ROOT)
    except Exception:  # noqa: BLE001
        print("   打不开资源管理器，路径是：" + ROOT)


def action_check():
    clear()
    run(sys.executable, "check.py")
    pause()


ACTIONS = {
    "1": action_build,
    "2": action_preview,
    "3": action_new_post,
    "4": action_pillow,
    "5": action_folder,
    "6": action_check,
}


def main():
    setup_console()
    if not os.path.isfile(os.path.join(ROOT, "build.py")):
        print("这个文件好像不在项目文件夹里，请把整个 muzetr 文件夹一起移动。")
        pause()
        return

    while True:
        show_menu()
        try:
            choice = input("   请输入数字后按回车（直接按回车 = 2 本地预览）： ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not choice:
            choice = "2"
        if choice in ("0", "q", "Q"):
            clear()
            print("\n   再见。下次双击 0-开始.cmd。\n")
            return
        action = ACTIONS.get(choice)
        if action:
            action()
        elif choice:
            print("\n   没有这个选项，按 0 到 6 输入。")
            pause("\n   按回车重来…")


if __name__ == "__main__":
    main()

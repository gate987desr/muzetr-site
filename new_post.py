#!/usr/bin/env python3
"""写新文章：一个问答式的向导，生成 content/posts/*.md。

    python new_post.py

回答几个问题，它会帮你写好 frontmatter（标题、日期、栏目、标签、摘要），
文件建好后可以直接打开编辑，最后还会问你要不要顺手生成网站。
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
POSTS_DIR = os.path.join(ROOT, "content", "posts")
CATEGORIES = ["札记", "书事", "器物", "城事", "技艺", "序跋"]

STARTER = """第一段从这里写起。第一个字会自动变成烫红色的首字下沉，所以别用图片开头。

## 小标题

正文段落之间空一行。想加粗就写 **两个星号**，想加链接就写 [文字](https://example.com)。

## 再一个标题

写完了把这段提示文字删掉就行。
"""


def ask(question, default=""):
    hint = "（直接回车＝%s）" % default if default else ""
    try:
        answer = input("%s%s： " % (question, hint)).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消，什么都没改。")
        sys.exit(0)
    return answer or default


def ascii_slug(text):
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text or "").strip("-").lower()
    return slug


def choose_category():
    print("\n文章放哪个栏目？")
    for index, name in enumerate(CATEGORIES, 1):
        print("  %d) %s" % (index, name))
    choice = ask("输入序号，或直接输入新的栏目名", "1")
    if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
        return CATEGORIES[int(choice) - 1]
    return choice or "札记"


def unique_path(slug):
    path = os.path.join(POSTS_DIR, slug + ".md")
    counter = 2
    while os.path.exists(path):
        path = os.path.join(POSTS_DIR, "%s-%d.md" % (slug, counter))
        counter += 1
    return path


def open_in_editor(path):
    """优先用 VS Code；没装就用记事本（.md 文件没有默认程序时会弹窗，所以直接指定）。"""
    if os.name != "nt":
        return
    code = shutil.which("code") or shutil.which("code.cmd")
    if code:
        try:
            subprocess.Popen(
                '"%s" "%s"' % (code, path),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except Exception:  # noqa: BLE001
            pass
    try:
        subprocess.Popen(["notepad.exe", path])
    except Exception:  # noqa: BLE001
        pass


def main():
    setup_console()
    os.makedirs(POSTS_DIR, exist_ok=True)

    print("=" * 46)
    print("  饮冰室 · 写新文章")
    print("=" * 46)

    title = ""
    while not title:
        title = ask("\n文章标题")
        if not title:
            print("  标题不能空着，再写一次。")

    category = choose_category()
    tags = ask("\n标签（多个用逗号隔开，可留空）")
    summary = ask("摘要（一句话，会出现在列表和搜索结果里，可留空）")

    today = datetime.date.today().strftime("%Y-%m-%d")
    guessed = ascii_slug(title) or "post-" + datetime.date.today().strftime("%Y%m%d")
    slug = ask("\n网址用的英文短名（小写字母/数字/横线）", guessed)
    slug = ascii_slug(slug) or "post-" + datetime.date.today().strftime("%Y%m%d")

    locked = ask("这篇文章要加密吗？输入 y 表示要，直接回车＝不加密", "n").lower().startswith("y")
    password = ""
    password_hint = ""
    if locked:
        while not password:
            password = ask("  设置一个口令（记牢，忘了就解不开了）")
        password_hint = ask("  给读者的一句提示（可留空）")

    tag_list = [item.strip() for item in re.split(r"[,，、\s]+", tags) if item.strip()]
    front = ["---", "title: %s" % title, "date: %s" % today, "category: %s" % category]
    if tag_list:
        front.append("tags: [%s]" % ", ".join(tag_list))
    if summary:
        front.append("summary: %s" % summary)
    front.append("featured: false")
    if locked:
        front.append("locked: true")
        front.append("password: %s" % password)
        if password_hint:
            front.append("password_hint: %s" % password_hint)
    front.append("---")

    path = unique_path(slug)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(front) + "\n\n" + STARTER)

    print("\n已建好：" + os.path.relpath(path, ROOT))
    if locked:
        print("口令是「%s」——写在 frontmatter 里，重新生成后就加密了。" % password)
    print("现在会帮你打开这个文件，写完正文保存即可。")
    open_in_editor(path)

    if ask("\n现在就生成网站吗？直接回车＝生成，输入 n 跳过", "y").lower().startswith("n"):
        print("好，记得之后运行 python build.py 或双击 build.cmd。")
        return

    print("\n正在生成…\n")
    result = subprocess.call([sys.executable, os.path.join(ROOT, "build.py")])
    if result == 0:
        print("\n完成。双击 preview.cmd 就能在浏览器里看到新文章。")
    else:
        print("\n生成失败了，把上面的报错信息发给我，我帮你看。")


if __name__ == "__main__":
    main()

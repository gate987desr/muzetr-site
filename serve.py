#!/usr/bin/env python3
"""本地预览：生成后的网站在这里跑起来。

    python serve.py            # http://127.0.0.1:8000 ，并自动打开浏览器
    python serve.py 8080       # 换一个端口
    python serve.py --no-open  # 不自动开浏览器
"""

from __future__ import annotations

import functools
import http.server
import os
import socketserver
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.console import setup as setup_console  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "public")
DEFAULT_PORT = 8000

EXTRA_TYPES = {
    ".webmanifest": "application/manifest+json",
    ".woff2": "font/woff2",
    ".json": "application/json; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".svg": "image/svg+xml",
    ".md": "text/markdown; charset=utf-8",
}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def guess_type(self, path):
        extension = os.path.splitext(str(path))[1].lower()
        if extension in EXTRA_TYPES:
            return EXTRA_TYPES[extension]
        return super().guess_type(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stdout.write("%s\n" % (fmt % args))
        sys.stdout.flush()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    setup_console()
    flags = [item for item in sys.argv[1:] if item.startswith("-")]
    plain = [item for item in sys.argv[1:] if not item.startswith("-")]
    auto_open = "--no-open" not in flags
    requested = int(plain[0]) if plain else int(os.environ.get("PORT", DEFAULT_PORT))

    if not os.path.isfile(os.path.join(ROOT, "index.html")):
        sys.exit("还没有 public/ 里的页面。先在项目文件夹里运行：python build.py")

    handler = functools.partial(Handler)
    httpd = None
    port = requested
    for candidate in range(requested, requested + 10):
        try:
            httpd = Server(("127.0.0.1", candidate), handler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        sys.exit("端口 %d 往后十个都被占用了，试试：python serve.py 9000" % requested)

    url = "http://127.0.0.1:%d" % port
    print("饮冰室 · 预览服务已启动：%s" % url)
    print("  改完内容记得先运行 python build.py，然后按 Ctrl+F5 强制刷新。")
    print("  Ctrl+C 停止。\n")

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass

    with httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止。")


if __name__ == "__main__":
    main()

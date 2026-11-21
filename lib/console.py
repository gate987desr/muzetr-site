"""让中文在 Windows 的控制台里正常显示。

Python 3.15 起 stdio 默认 UTF-8，而 cmd.exe / PowerShell 5.1 的代码页常常是 936，
于是中文会变成乱码。这里按控制台实际的代码页重设输出编码。
"""

import os
import sys
import unicodedata


def display_width(text):
    """中文按两个字符宽计算，用于对齐命令行里的表格。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in str(text))


def pad(text, size):
    text = str(text)
    return text + " " * max(1, size - display_width(text))


def setup():
    if not hasattr(sys.stdout, "reconfigure"):
        return
    # 真正在终端窗口里运行时，Python 3.15 自己就能正确处理中文，别去动它。
    try:
        if sys.stdout.isatty():
            return
    except Exception:  # noqa: BLE001
        pass
    encoding = "utf-8"
    if os.name == "nt":
        try:
            import ctypes

            codepage = ctypes.windll.kernel32.GetConsoleOutputCP()
            if codepage:
                encoding = "cp%d" % codepage
        except Exception:  # noqa: BLE001 - 取不到就用 UTF-8
            encoding = "utf-8"
    try:
        sys.stdout.reconfigure(encoding=encoding, errors="replace")
        sys.stderr.reconfigure(encoding=encoding, errors="replace")
    except Exception:  # noqa: BLE001
        pass

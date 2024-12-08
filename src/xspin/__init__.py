from math import ceil
import sys
from typing import Iterable
from unicodedata import category, combining, east_asian_width

if sys.platform == "win32":
    from ctypes import byref, c_ulong, windll, Structure
    from ctypes.wintypes import SHORT, _COORD, WORD  # type: ignore  "_COORD"

    KERNEL32 = windll.KERNEL32
    OUTHANDLE = KERNEL32.GetStdHandle(-12)  # Stderr handle
    GetConsoleScreenBuffer = KERNEL32.GetConsoleScreenBuffer

    def _():
        """
        Enable virtual terminal processing for windows
        so ansi escape codes are parsed.
        """
        VT_PROCESSING_MODE = 0x0004
        GetConsoleMode = KERNEL32.GetConsoleMode
        SetConsoleMode = KERNEL32.SetConsoleMode
        mode = c_ulong()
        GetConsoleMode(OUTHANDLE, byref(mode))
        mode.value |= VT_PROCESSING_MODE
        SetConsoleMode(OUTHANDLE, mode)

    class schedule:
        """
        Adds progress indication in windows terminal
        Read: https://learn.microsoft.com/en-us/windows/terminal/tutorials/progress-bar-sequences
        """

        @staticmethod
        def before():
            state.stream.write("\x1b]9;4;3;0\a")
            hide_cursor()

        @staticmethod
        def after():
            state.stream.write("\x1b]9;4;0;0\a")
            show_cursor()

    class _Rect(Structure):
        _fields_ = [
            ("left", SHORT),
            ("top", SHORT),
            ("right", SHORT),
            ("bottom", SHORT),
        ]

    class _ConsoleScreenBuffer(Structure):
        _fields_ = [
            ("a", _COORD),  # dwSize
            ("b", _COORD),  # dwCursorPosition
            ("c", WORD),  # wAttributes
            ("win", _Rect),  # srWindow
            ("d", _COORD),  # dwMaximumWindowSize
        ]

    CSBI = _ConsoleScreenBuffer()

    def get_console_width() -> int:
        if not GetConsoleScreenBuffer(byref(CSBI)):
            return 80
        return CSBI.win.right - CSBI.win.left + 1

else:
    import termios
    from sys import stdin
    from fcntl import ioctl
    from struct import unpack

    FD = stdin.fileno()

    class schedule:
        """
        Used to disable keystrokes from being echoed
        while the spinner is running
        """

        old_settings = termios.tcgetattr(FD)

        @classmethod
        def before(cls):
            new_settings = termios.tcgetattr(cls.FD)
            new_settings[3] = new_settings[3] & ~termios.ECHO
            termios.tcsetattr(cls.FD, termios.TCSADRAIN, new_settings)
            hide_cursor()

        @classmethod
        def after(cls):
            termios.tcsetattr(cls.FD, termios.TCSADRAIN, cls.old_settings)
            show_cursor()

    def get_console_width() -> int:
        try:
            rows, *_ = unpack("HHHH", ioctl(FD, termios.TIOCGWINSZ, "1234"))
            return rows
        except Exception:
            return 80


def hide_cursor():
    stream = state.stream
    stream.write("\x1b[?25l")
    stream.flush()


def show_cursor():
    stream = state.stream
    stream.write("\x1b[?25h")
    stream.flush()


class state:
    stream = sys.stdout.isatty() and sys.stdout or sys.stderr
    enabled = stream.isatty()


pattern = None


def get_pattern():
    global pattern
    if pattern:
        return pattern
    from re import compile

    pattern = compile("\x1b" r"[^m]*?m")
    return pattern


def chwidth(char: str) -> int:
    if category(char) in ["Cc", "Cf"]:
        return -1
    if combining(char):
        return 0
    width = east_asian_width(char)
    if width in ["W", "F"]:
        return 2
    return 1


def get_lines(text: str) -> Iterable[int]:
    console_width = get_console_width()
    text = get_pattern().sub("", text)
    length = text.isascii() and len or chwidth

    for line in text.splitlines():
        yield ceil(length(line) / console_width)

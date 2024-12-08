from math import ceil
import sys
from typing import Any, Iterable
from unicodedata import category, combining, east_asian_width
from threading import Thread
from time import sleep
from asyncio import create_task, sleep as asleep, CancelledError, run as arun

if sys.platform == "win32":
    from ctypes import byref, c_ulong, windll, Structure
    from ctypes.wintypes import SHORT, WORD

    KERNEL32 = windll.KERNEL32
    OUTHANDLE = KERNEL32.GetStdHandle(-12)  # Stderr handle
    GetConsoleScreenBuffer = KERNEL32.GetConsoleScreenBufferInfo

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

    class _COORD(Structure):
        _fields_ = [("X", SHORT), ("Y", SHORT)]

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
    handle: Any = None
    instance: Any = None


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


def clear_lines(lines: int):
    write = state.stream.write
    write("\x1b[1G")
    for i in range(lines):
        if i > 0:
            write("\x1b[1A")
        write("\x1b[2K\x1b[1G")


def live_text(frames: Iterable[str]):
    write = state.stream.write
    for frame in frames:
        write(frame)
        yield get_lines(frame)


class SyncRuntime:
    __slots__ = "running", "delay", "message"

    def __init__(self, delay: int) -> None:
        self.running = False
        self.delay = delay / 1000
        self.message = ""

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *e: Any):
        return self.stop()

    def render(self, message: str | None = None, end: bool = False) -> Iterable[int]:
        raise NotImplementedError()

    def run(self):
        clearable = None
        delay = self.delay
        try:
            while self.running:
                clearable = self.render(self.message or None)
                self.message = ""
                sleep(delay)
                clear_lines(sum(clearable))
        except Exception:
            if clearable:
                clear_lines(sum(clearable))

    def start(self):
        if self.running:
            return
        if state.instance:
            stop()
        state.instance = self
        self.running = True
        handle = Thread(target=self.run, daemon=True)
        handle.start()
        state.handle = handle

    def stop(self, epilogue: str | None = None):
        if not self.running:
            return
        self.running = False
        if state.handle:
            state.handle.join()
        message = self.message
        if epilogue:
            message = f"{message}{epilogue}\n"
        self.render(message, True)
        state.handle = None
        state.instance = None


class AsyncRuntime:
    __slots__ = "running", "delay", "message"

    def __init__(self, delay: int) -> None:
        self.running = False
        self.delay = delay / 1000
        self.message = ""

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *e: Any):
        return await self.stop()

    def render(self, message: str | None = None, end: bool = False) -> Iterable[int]:
        raise NotImplementedError()

    async def run(self):
        clearable = None
        delay = self.delay
        try:
            while self.running:
                clearable = self.render(self.message or None)
                self.message = ""
                await asleep(delay)
                clear_lines(sum(clearable))
        except Exception:
            if clearable:
                clear_lines(sum(clearable))

    async def start(self):
        if self.running:
            return
        if state.instance:
            stop()
        state.instance = self
        self.running = True
        handle = create_task(self.run())
        state.handle = handle

    async def stop(self, epilogue: str | None = None):
        if not self.running:
            return
        self.running = False
        if state.handle:
            try:
                await state.handle
            except CancelledError:
                pass
        message = self.message
        if epilogue:
            message = f"{message}{epilogue}\n"
        self.render(message, True)
        state.handle = None
        state.instance = None


def stop():
    if isinstance(state.handle, SyncRuntime):
        state.handle.stop()
    elif isinstance(state.handle, AsyncRuntime):
        arun(state.handle.stop())

from math import ceil
import sys
from typing import (
    Any,
    Callable,
    Concatenate,
    Coroutine,
    Iterable,
    Optional,
    ParamSpec,
    Self,
    TypeVar,
)
from unicodedata import category, combining, east_asian_width
from threading import Thread
from time import sleep
from asyncio import create_task, sleep as asleep, CancelledError, run as arun
from functools import wraps
from types import MethodType

if sys.platform == "win32":
    from ctypes import byref, c_ulong, windll, Structure
    from ctypes.wintypes import SHORT, USHORT

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

    _()

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
            ("c", USHORT),  # wAttributes
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
            new_settings = termios.tcgetattr(FD)
            new_settings[3] = new_settings[3] & ~termios.ECHO
            termios.tcsetattr(FD, termios.TCSADRAIN, new_settings)
            hide_cursor()

        @classmethod
        def after(cls):
            termios.tcsetattr(FD, termios.TCSADRAIN, cls.old_settings)
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


def mchwidth(text: str):
    return sum(map(chwidth, text))


def get_lines(text: str) -> Iterable[int]:
    console_width = get_console_width()
    text = get_pattern().sub("", text)
    length = text.isascii() and len or mchwidth

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
    flush = state.stream.flush
    for frame in frames:
        write(frame)
        flush()
        yield get_lines(frame)


PS = ParamSpec("PS")
R = TypeVar("R")


class SyncRuntime:

    def __init__(self, delay: int) -> None:
        self.running = False
        self.delay = (min(0, delay) or 50) / 1000
        self.message = ""

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *e: Any):
        return self.stop()

    def render(self, message: str | None = None) -> Iterable[int]:
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
        if self.running or not state.enabled:
            return
        if state.instance:
            stop()
        schedule.before()
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
        state.stream.write(message)
        schedule.after()
        state.handle = None
        state.instance = None

    def bind(self, fn: Callable[Concatenate[Self, PS], R]) -> Callable[PS, R]:
        @wraps(fn)
        def wrapper(this: Self, *args: PS.args, **kwargs: PS.kwargs):
            with this:
                return fn(this, *args, **kwargs)

        return MethodType(wrapper, self)


class AsyncRuntime:
    __slots__ = "running", "delay", "message"

    def __init__(self, delay: int) -> None:
        self.running = False
        self.delay = (min(0, delay) or 50) / 1000
        self.message = ""

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *e: Any):
        return await self.stop()

    def render(self, message: str | None = None) -> Iterable[int]:
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
        if self.running or not state.enabled:
            return
        if state.instance:
            stop()

        schedule.before()
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
        state.stream.write(message)
        schedule.after()
        state.handle = None
        state.instance = None

    def bind(
        self, fn: Callable[Concatenate[Self, PS], Coroutine[Any, Any, R]]
    ) -> Callable[PS, Coroutine[Any, Any, R]]:
        @wraps(fn)
        async def wrapper(this: Self, *args: PS.args, **kwargs: PS.kwargs):
            async with this:
                return await fn(this, *args, **kwargs)

        return MethodType(wrapper, self)


def stop():
    if isinstance(state.handle, SyncRuntime):
        state.handle.stop()
    elif isinstance(state.handle, AsyncRuntime):
        arun(state.handle.stop())


def force():
    state.enabled = True


class Frames:
    def __init__(self, format: str, label: str, symbols: Iterable[str]) -> None:
        if not isinstance(symbols, (str, set, tuple, list)):
            symbols = list(symbols)
        self.symbols = symbols
        self.label = label
        self.format = format
        self.iterator = None

    def __next__(self):
        if self.iterator:
            return next(self.iterator)
        self.iterator = iter(self.iter())
        return next(self.iterator)

    def __iter__(self):
        return self

    def iter(self):
        symbols = self.symbols
        format = self.format
        while True:
            for symbol in symbols:
                yield format.format(symbol=symbol, label=self.label)


class Spinner:

    def __init__(
        self,
        label: Optional[str] = None,
        format: Optional[str] = None,
        symbols: Optional[Iterable[str]] = None,
    ) -> None:
        self.frames = Frames(
            format or "{symbol} {label}",
            label or "Loading ...",
            symbols or r"\|/-",
        )
        self.running: bool
        self.message: str
        self.live = iter(live_text(self.frames))

    def render(self, message: str | None = None) -> Iterable[int]:
        if message:
            state.stream.write(message)
        lines = next(self.live)
        return lines

    def echo(self, *values: Any, sep: str = ""):
        message = sep.join(map(str, values)) + "\n"
        if self.running:
            setattr(self, "message", self.message + message)
            return
        state.stream.write(message)

    @property
    def label(self) -> str:
        return self.frames.label

    @label.setter
    def label(self, label: str):
        self.frames.label = label


class Xspin(Spinner, SyncRuntime):
    def __init__(
        self,
        label: str | None = None,
        format: str | None = None,
        symbols: Iterable[str] | None = None,
        delay: Optional[int] = None,
    ) -> None:
        SyncRuntime.__init__(self, delay or 50)
        Spinner.__init__(
            self,
            label,
            format,
            symbols,
        )


class Axspin(Spinner, AsyncRuntime):
    def __init__(
        self,
        label: str | None = None,
        format: str | None = None,
        symbols: Iterable[str] | None = None,
        delay: Optional[int] = None,
    ) -> None:
        AsyncRuntime.__init__(self, delay or 50)
        Spinner.__init__(
            self,
            format,
            label,
            symbols,
        )


class CustomSpinner(SyncRuntime):
    def __init__(self, delay: Optional[int] = None) -> None:
        super().__init__(delay or 50)
        self.live = live_text(self.frames())

    def frames(self) -> Iterable[str]:
        raise NotImplementedError()

    def render(self, message: str | None = None) -> Iterable[int]:
        if message:
            state.stream.write(message)
        return next(self.live)


class CustomAspinner(AsyncRuntime):
    def __init__(self, delay: Optional[int] = None) -> None:
        super().__init__(delay or 50)
        self.live = live_text(self.frames())

    def frames(self) -> Iterable[str]:
        raise NotImplementedError()

    def render(self, message: str | None = None) -> Iterable[int]:
        if message:
            state.stream.write(message)
        return next(self.live)

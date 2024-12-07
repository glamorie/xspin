import sys

if sys.platform == "win32":

    def _():
        """
        Enable virtual terminal processing for windows
        so ansi escape codes are parsed.
        """
        try:
            from ctypes import byref, c_ulong, windll
        except ImportError:
            return
        VT_PROCESSING_MODE = 0x0004
        OUTPUT_HANDLE = sys.stdout.isatty() and -11 or -12
        kernel32 = windll.kernel32
        kernel32 = windll.kernel32
        GetStdHandle = kernel32.GetStdHandle
        GetConsoleMode = kernel32.GetConsoleMode
        SetConsoleMode = kernel32.SetConsoleMode
        handle = GetStdHandle(OUTPUT_HANDLE)
        mode = c_ulong()
        GetConsoleMode(handle, byref(mode))
        mode.value |= VT_PROCESSING_MODE
        SetConsoleMode(handle, mode)

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

else:
    import termios
    from sys import stdin

    class schedule:
        """
        Used to disable keystrokes from being echoed
        while the spinner is running
        """

        fd = stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        @classmethod
        def before(cls):
            new_settings = termios.tcgetattr(cls.fd)
            new_settings[3] = new_settings[3] & ~termios.ECHO
            termios.tcsetattr(cls.fd, termios.TCSADRAIN, new_settings)
            hide_cursor()

        @classmethod
        def after(cls):
            termios.tcsetattr(cls.fd, termios.TCSADRAIN, cls.old_settings)
            show_cursor()


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

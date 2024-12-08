"""
# xspin
Python module for creating console spinners.

## Types
- SyncRuntime 
- AyncRuntime 
- Spinner 
- Xspin 
- Axspin

# Functions
- stop
"""

from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    ParamSpec,
    TypeVar,
    Concatenate,
    Self,
    Coroutine,
)

PS = ParamSpec("PS")
A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")

class SyncRuntime:
    """
    Base class for spinners that are used in
    syncronous programs.

    # Features
    - Context manager
    - Binding function to the spinner
    - start and stoping spinner.
    """

    def __init__(self, delay: int) -> None:
        """
        # Params
        * `delay` Time interval between each render.
        """

    def __enter__(self) -> Self:
        pass

    def __exit__(self, *e: object) -> None:
        pass

    def render(self, message: str | None = None) -> Iterable[str]:
        """
        Defined by the subclass. It is called by the spinner's main loop
        and handles rendering the main spinner frame.

        # Params
        * `message` Optional string. Passed down from when the echo method is called.

        # Returns
        It should return an iterable of integers used to compute the lines
        the spinner frame takes up in the console.

        # Note
        The module provides base classes that remove the need to implement this method
        yourself.
        """

    def start(self) -> None:
        """
        Starts the spinner and runs it in a separate thread.
        """

    def stop(self, epilogue: str | None = None) -> None:
        """
        Stops the spinner if its already running.

        # Params
        * `epilogue` The text to be rendered when the spinner is cleared.

        # Note
        When using the context manager, the `echo` method can be used
        and the message will function as an epilogue.
        """

    def bind(self, fn: Callable[Concatenate[Self, PS], A]) -> Callable[PS, A]:
        """
        Binds the spinner to some function such that the spinner runs in
        the background when the function executes.

        # Params
        * `fn` The function to bind the spinner to. It should take in an instance
            of the spinner as the first parameter so it can be used for logging.

        # Return
        A method bound to the spinner instance.

        # Example

        >>> sp = Xspin("Running task ...")
            @sp.bind
            def pause(sp: Xspin, delayms: int):
                sleep(delayms / 1000)
                sp.echo("Done!")

        >>> pause(3)
        """

class AsyncRuntime:
    """
    Base class for spinners that are used in
    syncronous programs.

    # Features
    - Async context manager
    - Binding async function to the spinner
    - start and stoping spinner
    """

    def __init__(self, delay: int) -> None:
        """
        # Params
        * `delay` Time interval between each render.
        """

    async def __aenter__(self) -> Self:
        pass

    async def __aexit__(self, *e: object) -> None:
        pass

    def render(self, message: str | None = None) -> Iterable[str]:
        """
        Defined by the subclass. It is called by the spinner's main loop
        and handles rendering the main spinner frame.

        # Params
        * `message` Optional string. Passed down from when the echo method is called.

        # Returns
        It should return an iterable of integers used to compute the lines
        the spinner frame takes up in the console.

        # Note
        The module provides base classes that remove the need to implement this method
        yourself.
        """

    async def start(self) -> None:
        """
        Starts the spinner and runs it in a separate thread.
        """

    async def stop(self, epilogue: str | None = None) -> None:
        """
        Stops the spinner if its already running.

        # Params
        * `epilogue` The text to be rendered when the spinner is cleared.

        # Note
        When using the context manager, the `echo` method can be used
        and the message will function as an epilogue.
        """

    def bind(
        self, fn: Callable[Concatenate[Self, PS], Coroutine[A, B, C]]
    ) -> Callable[PS, Coroutine[A, B, C]]:
        """
        Binds the spinner to some async function such that the spinner runs in
        the background when the function executes.

        # Params
        * `fn` The function to bind the spinner to. It should take in an instance
            of the spinner as the first parameter so it can be used for logging.

        # Return
        A method bound to the spinner instance.

        # Example

        >>> sp = Xspin("Running task ...")
            @sp.bind
            async def pause(sp: Xspin, delayms: int):
                await sleep(delayms / 1000)
                sp.echo("Done!")

        >>> await pause(3)
        """

class Spinner:
    """
    Base class for spinners that use python's format templating
    to define how the spinner looks like.
    The format string used to define the position of the `symbols`
    and the `label` relative to each other.
    >>> sp = Xspin(format="{symbol} {label}")
    """

    def __init__(
        self,
        label: Optional[str] = None,
        format: Optional[str] = None,
        symbols: Optional[Iterable[str]] = None,
    ) -> None:
        """
        # Params
        * `label`   The text displayed next to the spinner symbols.
        * `symbols` The characters that change when the spinner re-renders.
        * `format`  String used to define the position of the symbols and
            the label relative to each other.
        """

    def echo(self, *values: Any, sep: str = " ") -> None:
        """
        # Params
        * `values` Objects to log out.
        * `sep`    String used to join the objects when mapped to strings.
        """

    @property
    def label(self) -> str:
        """The text atatched to the spinner symbols."""

    @label.setter
    def label(self, label: str) -> None:
        pass

class Xspin(Spinner, SyncRuntime):
    def __init__(
        self,
        label: str | None = None,
        format: str | None = None,
        symbols: Iterable[str] | None = None,
        delay: Optional[int] = None,
    ) -> None:
        """
        # Params
        * `label`   The text displayed next to the spinner symbols.
        * `symbols` The characters that change when the spinner re-renders.
        * `format`  String used to define the position of the symbols and
            the label relative to each other.
        * `delay`   Time interval between each spinner frame render.
        """

class Axspin(Spinner, AsyncRuntime):
    def __init__(
        self,
        label: str | None = None,
        format: str | None = None,
        symbols: Iterable[str] | None = None,
        delay: Optional[int] = None,
    ) -> None:
        """
        # Params
        * `label`   The text displayed next to the spinner symbols.
        * `symbols` The characters that change when the spinner re-renders.
        * `format`  String used to define the position of the symbols and
            the label relative to each other.
        * `delay`   Time interval between each spinner frame render.
        """

class CustomSpinner(SyncRuntime):
    """
    Base class for syncronous spinners.
    The `frames` method should be implemented.
    """

    def __init__(self, delay: Optional[int] = None) -> None:
        """
        # Params
        * `delay` Time interval between each frame render.
        """

    def frames(self) -> Iterable[str]:
        """
        Should return an iterable of strings representing
        how the spinner frame looks like.
        """

class CustomAspinner(AsyncRuntime):
    """
    Base class for asyncronous spinners.
    The `frames` method should be implemented.
    """

    def __init__(self, delay: Optional[int] = None) -> None:
        """
        # Params
        * `delay` Time interval between each frame render.
        """

    def frames(self) -> Iterable[str]:
        """
        Should return an iterable of strings representing
        how the spinner frame looks like.
        """

def stop() -> None:
    """Stops the spinner running currently."""

def force() -> None:
    """
    Force the render of the spinner even when the stream
    is not tty.
    """

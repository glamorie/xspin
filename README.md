# xspin
Python module for creating console spinners.
![PyPI version](https://badge.fury.io/py/xspin.svg)
![Build Status](https://github.com/glamorie/xspin/workflows/release/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Spinner runtimes
There are two types of spinner's based on the kind of program being 
run.

- ### SyncRuntime
This is the base class for spinners running in a blocking program.
They run in a separate thread. These include [Xspin](#xspin) and [CustomSpinner](#customspinner)

- ### AsyncRuntime 
This is the base class for spinners running in an async program.
They run in a separate thread. These include [Axspin](#xspin) and [CustomAspinner](#customaspinner)

## Running spinners.
There are three ways in which a spinner instance can be run. These are implemented by
the runtime base classes hence apply to any of their subclasses.

- ### `start` and `stop`
These are methods used to start and stop a spinner.
```python 
spinner = Xspin(label="Loading ...")
spinner.start()
do_work()
spinner.stop("Done!")
```
For async spinners, these methods have to be awaited.
```python 
async def main():
    spinner = Axspin(label="Loading ...")
    await spinner.start()
    await do_work()
    await spinner.stop("Done!")
```

- ### Context manager
The runtimes also implement the context manager protocal.
For sync spinners,
```python
with Xspin("Loading ...") as sp:
    do_work()
    sp.echo("Done!")
```
For async spinners,
```python
async def main():
    async with Axspin("Loading ...") as sp:
        await do_work()
        sp.echo("Done!")
```

- ### Binding the spinner to a function.
When a spinner is bound to a function, it returns a method
which when called runs the spinner in the background as it executes.
The function being bound must take in the spinner instance as the first
argument. This is useful for ensuring the spinner is accessible from inside
the function if logging is required.
```python
sp = Xspin("Doing work ...")

@sp.bind 
def do_work(sp: Xspin, some_arg: str, other: int ):
    sp.echo(f" {some_arg} {other}")
    ...
    sp.echo("Done!")

do_work("Some arg", 1 )

```
Async spinners should be bound to async functions.
```python
sp = Axspin("Doing work ...")

@sp.bind 
async def download(sp: Xspin, url: str, file: str):
    sp.echo(f" * Downloading <{other}>")
    ...
    sp.echo(f" * <{other}> -> {[file]}!")

async def main():
    await download("https://www.example.com/image.png", "image.png")
```

## Interfacing with the runtimes.
When inheriting from a runtime base class, the runtime expects the 
`render` method to be defined. This is the function that is called
on each update. It should return an iterable of integers which 
when summed returns the lines the text takes up in the terminal. This is 
rarely required since the module provides preconfigured classes that implement
the render method automatically. These are

- ### Xspin and Axspin
These spinners use python's format templating to define the frames of the spinner.
The format should contain the keys `symbol` and `label`. The symbols are cycled over
and formated based on the format specified.
```python
sp = Xspin(label = "Loading ...", format="{symbol} {label}",symbols=r"\|/-")
```
The symbols are just an iterable of strings. 
> **NOTE** If the generator is not a builtin collection, list is called on so the 
values are reused. Doing things for infinite iterables like itertools `cycle` may lead 
to memory errors.

- ### CustomSpinner and CustomAspinner
When inheriting from these base classes, they rely on the `frames` being implemented to return
an iterable of strings representing the spinner frame. You can define it as a generator 
and store the spinner state in the instance itself.

```python
class MySpinner(CustomSpinner):
    def __init__(self, count: int):
        super().__init__(delay=50)
        self.count = count

    def frames(self):
        for i in range(self.count):
            yield f"Count {i}"

with MySpinner(30) as sp:
    ... # do something
    sp.echo("Done!")     
```

## Unix Tingz 
When the spinner runs, it disables keystrokes from being echoed so they don't interfere with
the spinner being rendered.
<img src="https://raw.githubusercontent.com/glamorie/xspin/main/media/ubuntu-demo.gif" alt="Ubuntu Demo: Spinner Running in ubuntu with keystrokes echoing disabled.">


## Windows Tingz
On windows, virtual terminal mode is enabled in order for colors and ansi escape codes to work. This allows for the spinners to be rendered even on 
the old `conhost.exe` emulator.
<img src="https://raw.githubusercontent.com/glamorie/xspin/main/media/conhost.gif" alt="Windows Conhost Demo: Demonstrates how the spinner runs with virtual terminal mode enabled on Windows' old `conhost.exe`.">

The spinner also uses escape codes specified [here](https://learn.microsoft.com/en-us/windows/terminal/tutorials/progress-bar-sequences) to enable progress indication on windows terminal's titlebar and taskbar.
<img src="https://raw.githubusercontent.com/glamorie/xspin/main/media/wt.gif" alt="Windows Terminal Demo: Demonstrates titlebar progress indication when the spinner runs.">

## License
[MIT](LICENSE)
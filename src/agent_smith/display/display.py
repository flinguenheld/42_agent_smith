from typing import Protocol

from rich.console import Console
from rich.rule import Rule
from rich.syntax import Syntax

from agent_smith.data import CODE_THEME, DebugLevel
from agent_smith.display.progress import TaskProgress
from agent_smith.models import DebugView


class Viewable(Protocol):
    """Anything Display.debug can show: it has a debug_view method."""

    def debug_view(self, level: DebugLevel) -> DebugView:
        """Return the text and code to show at this debug level."""
        ...


class Display:
    """Helpers to print with colors and debug levels."""

    level: DebugLevel = DebugLevel.OFF
    _out = Console(highlight=False, soft_wrap=True, markup=False)
    _err = Console(stderr=True, highlight=False, soft_wrap=True, markup=False)

    @classmethod
    def progress(cls) -> TaskProgress:
        """Return an empty progress bar on stderr; Display prints go above."""
        return TaskProgress(cls._err)

    # ---------------------------------------------------- SET DEBUG LEVEL ----
    @classmethod
    def set_debug_level(cls, level: DebugLevel) -> None:
        """Change the debug level, e.g. from the --debug flag."""
        cls.level = level

    # -------------------------------------------------------------- ERROR ----
    @classmethod
    def error(cls, title: str, message: str) -> None:
        """Print an error in red on stderr."""
        header = f"\n--- {title} ERROR ---\n"
        footer = "-" * (len(header) - 2)

        cls._err.print(header, style="red")
        for line in message.splitlines():
            cls._err.print(f"   {line}", style="red")
        cls._err.print(footer, style="red")

    # --------------------------------------------------------------- INFO ----
    @classmethod
    def info(cls, message: str) -> None:
        """Print an information message in green on stdout."""
        cls._out.print(message, style="green")

    # ------------------------------------------------------------- OUTPUT ----
    @classmethod
    def output(cls, text: str, ok: bool = True) -> None:
        """Print text on stdout as it is: default color, or red if not ok.

        emoji=False: user output like ":fire:" must not become an emoji.
        """
        cls._out.print(text, style=None if ok else "red", emoji=False)

    # --------------------------------------------------------------- CODE ----
    @classmethod
    def _syntax(cls, code: str) -> Syntax:
        """Return code as colored Python with line numbers."""
        code = code.rstrip()  # no empty numbered line at the end
        return Syntax(code, "python", theme=CODE_THEME, line_numbers=True)

    # -------------------------------------------------------------- DEBUG ----
    @classmethod
    def debug(
        cls,
        message: str | Viewable | None,
        title: str = "Debug",
        level: DebugLevel = DebugLevel.ON,
    ) -> None:
        """Print message in magenta on stderr if level <= Display.level.

        A string is shown on one titled line. A model is shown through its
        debug_view, between two rules: text, colored code, then output.
        """

        if level > cls.level or not message:
            return
        if isinstance(message, str):
            cls._print_line(title, message)
        else:
            cls._print_block(title, message.debug_view(cls.level))

    @classmethod
    def _print_line(cls, title: str, text: str) -> None:
        """Print text after "title  ->"; later lines are aligned under it."""

        prefix = f"     {title}  -> "
        blank = " " * len(prefix)
        first, *rest = text.splitlines()

        cls._err.print(prefix + first, style="magenta")
        for line in rest:
            cls._err.print(blank + line, style="magenta")
        cls._err.print()

    @classmethod
    def _print_block(cls, title: str, view: DebugView) -> None:
        """Print a view between two rules: text, code, then its output."""

        cls._err.print(Rule(title, style="magenta"))
        cls._err.print(view.text, style="magenta")
        if view.code.strip():
            cls._err.print()
            cls._err.print(cls._syntax(view.code))
        if view.output.strip():
            cls._err.print()
            cls._err.print("Output:", style="magenta")
            for line in view.output.rstrip().splitlines():
                cls._err.print(f"  {line}")  # default color: not ours
        cls._err.print(Rule(style="magenta"))
        cls._err.print()  # blank line before the next block

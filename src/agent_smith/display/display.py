from pydantic import BaseModel
from rich.console import Console

from agent_smith.data import DebugLevel
from agent_smith.display.pretty import pretty_format


class Display:
    """Helpers to print with colors and debug levels."""

    level: DebugLevel = DebugLevel.OFF
    _out = Console(highlight=False, soft_wrap=True, markup=False)
    _err = Console(stderr=True, highlight=False, soft_wrap=True, markup=False)

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

    # -------------------------------------------------------------- DEBUG ----
    @classmethod
    def debug(
        cls,
        message: str | BaseModel | None,
        title: str = "Debug",
        level: DebugLevel = DebugLevel.SUMMARY,
        full: bool = False,
    ) -> None:
        """Print message in magenta on stderr if level <= Display.level.

        A model is shown as its summary, or with all its fields if full is
        True or at FULL level.
        """

        if level > cls.level or not message:
            return

        text = cls._to_text(message, full)
        prefix = f"     {title}  -> "
        blank = " " * len(prefix)
        first, *rest = text.splitlines()

        cls._err.print(prefix + first, style="magenta")
        for line in rest:
            cls._err.print(blank + line, style="magenta")
        cls._err.print()

    @classmethod
    def _to_text(cls, message: str | BaseModel, full: bool) -> str:
        """Return message as text: a model's summary, or all its fields."""

        if isinstance(message, str):
            return message
        if full or cls.level >= DebugLevel.FULL:
            return pretty_format(message.model_dump())
        return str(message)

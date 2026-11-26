"""The interactive sandbox: read code, run it in the sandbox, print."""

from __future__ import annotations

import codeop
from collections.abc import Callable

from agent_smith.data import (
    REPL_CONTINUE,
    REPL_EXIT,
    REPL_PROMPT,
    SANDBOX_FILENAME_PREFIX,
)
from agent_smith.display import Display
from agent_smith.sandbox.host import Sandbox
from agent_smith.sandbox.result import ExecResult

Reader = Callable[[str], str]  # like input(): prompt -> line, EOFError at end

_FILENAME = SANDBOX_FILENAME_PREFIX + "repl>"
_INTERRUPTED = "KeyboardInterrupt: sandbox restarted, variables are lost"


def is_complete(source: str) -> bool:
    """False while Python waits for more lines (after `def f():`).

    Only compiles, never runs: the code runs in the worker. "single" is
    the mode of Python's own prompt: a block ends with an empty line.
    """

    try:
        return codeop.compile_command(source, _FILENAME, "single") is not None
    except (SyntaxError, ValueError, OverflowError):
        return True


def read_entry(read: Reader) -> str:
    """Read lines until they form a complete entry. EOFError at the end."""
    lines = [read(REPL_PROMPT)]
    while not is_complete("\n".join(lines)):
        lines.append(read(REPL_CONTINUE))
    return "\n".join(lines)


def show(result: ExecResult) -> None:
    """Print a run as the LLM sees it; nothing for a silent success."""
    if result.ok and not (result.stdout or result.stderr):
        if result.final_answer is None:
            return
    Display.output(result.to_observation(), result.ok)
    if result.final_answer is not None:
        Display.info(f"final_answer: {result.final_answer}")


def _exit_code(exc: SystemExit) -> int:
    """sys.exit() / SystemExit code as a process exit code."""
    if exc.code is None:
        return 0
    return exc.code if isinstance(exc.code, int) else 1


def run_repl(sbx: Sandbox, read: Reader = input) -> int:
    """Read, run and print until `exit` or EOF; return the exit code."""
    while True:
        try:
            code = read_entry(read)
        except EOFError:
            Display.output("")
            return 0
        except KeyboardInterrupt:  # CTRL-C at the prompt: drop entry
            Display.output("\nKeyboardInterrupt")
            continue
        if code.strip() in REPL_EXIT:
            return 0
        if not code.strip():
            continue
        try:
            show(sbx.run(code))
        except KeyboardInterrupt:  # CTRL-C while running: worker killed
            Display.output(_INTERRUPTED, ok=False)
        except SystemExit as exc:  # Raised by user code
            return _exit_code(exc)

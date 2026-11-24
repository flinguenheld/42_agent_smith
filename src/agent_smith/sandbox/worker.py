"""Child process: receives the code from the host, runs it, reports back.

Started by host.py as: python -I -c BOOTSTRAP <src_root> <parent_pid>
Never import this module in the parent process.

Security is NOT enforced yet. Every place where it will be is a call on
`policy` (see the Policy protocol below). Today that object is NoPolicy,
which allows everything; later policy.py provides a real one and main()
picks it instead. Nothing else in this file has to change.
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import io
import itertools
import json
import linecache
import os
import signal
import sys
import traceback
from collections.abc import Iterator
from contextlib import redirect_stderr, redirect_stdout
from typing import IO, Any, Literal, Protocol

from . import protocol as p
from .config import SandboxConfig
from .policy import SandboxPolicy
from .result import Status

_THIS_FILE = os.path.realpath(__file__)

# ------------------------------------------------------------------ policy


class Policy(Protocol):
    """What the worker asks of a security policy. Four hooks:

    check(tree)      before running: list of problems, [] = accepted
    builtins()       the __builtins__ dict given to user code
    lock_down()      once, before the first run: rlimits, audit hook...
    trusted()        context manager: worker-internal code that must not
                     be blocked (e.g. reading traceback frames)
    violations       exception types meaning "the policy said no"
    """

    violations: tuple[type[BaseException], ...]

    def check(self, tree: ast.Module) -> list[str]: ...

    def builtins(self) -> dict[str, Any]: ...

    def lock_down(self) -> None: ...

    def trusted(self) -> contextlib.AbstractContextManager[None]: ...


class NoPolicy:
    """Allows everything. Placeholder until policy.py is written."""

    violations: tuple[type[BaseException], ...] = ()

    def __init__(self, cfg: SandboxConfig) -> None:
        self.cfg = cfg

    def check(self, tree: ast.Module) -> list[str]:
        return []

    def builtins(self) -> dict[str, Any]:
        return dict(vars(builtins))

    def lock_down(self) -> None:
        pass

    @contextlib.contextmanager
    def trusted(self) -> Iterator[None]:
        yield


# ----------------------------------------------------------------- channel


class _Channel:
    """The two private pipe ends used for the protocol."""

    def __init__(self) -> None:
        # Keep our own copies of fd 0/1, then point 0/1 at /dev/null so
        # nothing user code writes to "stdout" can corrupt the protocol.
        self.inp: IO[bytes] = os.fdopen(os.dup(0), "rb")
        self.out: IO[bytes] = os.fdopen(os.dup(1), "wb")
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.close(devnull)

    def send(self, msg: Any) -> None:
        p.send(self.out, msg)

    def receive(self) -> Any:
        msg = p.receive_from_parent(self.inp)
        if msg is None:  # EOF: the parent closed us or died
            os._exit(0)
        return msg


class _StreamToParent(io.TextIOBase):
    """Replaces sys.stdout / sys.stderr: every write is sent at once, so
    output printed before a timeout still reaches the host."""

    def __init__(
        self, chan: _Channel, name: Literal["stdout", "stderr"]
    ) -> None:
        self._chan = chan
        self._name = name

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        if not isinstance(s, str):
            raise TypeError(
                f"write() argument must be str, not {type(s).__name__}"
            )
        if s:
            self._chan.send(p.Output(stream=self._name, data=s))
        return len(s)


# ---------------------------------------------------------------- namespace


class ToolError(Exception):
    """A tool failed on the host side; the message comes from the host."""


def _make_tool(chan: _Channel, name: str, ids: Iterator[int]) -> Any:
    """Stub for a host-side tool: sends ToolCall, waits for ToolResult."""

    def tool(*args: Any, **kwargs: Any) -> str:
        if args:
            raise TypeError(
                f"{name}() takes keyword arguments only, "
                f"e.g. {name}(arg=value)"
            )
        try:
            json.dumps(kwargs)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{name}(): arguments must be JSON serializable ({exc})"
            ) from None
        call_id = next(ids)
        chan.send(p.ToolCall(call_id=call_id, name=name, kwargs=kwargs))
        reply = chan.receive()
        if not isinstance(reply, p.ToolResult) or reply.call_id != call_id:
            raise RuntimeError("sandbox protocol error during tool call")
        if not reply.ok:
            raise ToolError(reply.value)
        return reply.value

    tool.__name__ = tool.__qualname__ = name
    return tool


def _build_namespace(
    chan: _Channel, policy: Policy, tool_names: list[str]
) -> dict[str, Any]:
    def final_answer(answer: Any) -> None:
        """Submit the final answer and end the task."""
        chan.send(p.FinalAnswer(value=str(answer)))

    ns: dict[str, Any] = {
        "__builtins__": policy.builtins(),
        "__name__": "__main__",
        "final_answer": final_answer,
    }
    ids = itertools.count(1)
    for name in tool_names:
        ns[name] = _make_tool(chan, name, ids)
    return ns


# ---------------------------------------------------------------------- run


def _format_error(exc: BaseException, policy: Policy) -> str:
    """Traceback without this file's frames (the LLM doesn't need them)."""
    with policy.trusted():
        frames = [
            f
            for f in traceback.extract_tb(exc.__traceback__)
            if os.path.realpath(f.filename) != _THIS_FILE
        ]
    text = "".join(traceback.format_exception_only(type(exc), exc))
    if not frames:
        return text
    return (
        "Traceback (most recent call last):\n"
        + "".join(traceback.format_list(frames))
        + text
    )


def _done(status: Status, error: str | None = None) -> p.Done:
    return p.Done(status=status.value, error=error)


def _run(
    code: str, ns: dict[str, Any], policy: Policy, filename: str
) -> p.Done:
    try:
        tree = ast.parse(code, filename)
    except SyntaxError as exc:
        return _done(Status.SYNTAX_ERROR, _format_error(exc, policy))

    problems = policy.check(tree)
    if problems:
        return _done(
            Status.POLICY_VIOLATION,
            "Code rejected before execution:\n" + "\n".join(problems),
        )

    # Register the source so tracebacks can show the failing line.
    linecache.cache[filename] = (
        len(code),
        None,
        code.splitlines(True),
        filename,
    )
    # REPL behaviour: a final expression is evaluated and printed.
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = ast.Expression(tree.body[-1].value)
        tree.body.pop()

    try:
        exec(compile(tree, filename, "exec"), ns)
        if last is not None:
            value = eval(compile(last, filename, "eval"), ns)
            if value is not None:
                print(repr(value))
    except policy.violations as exc:
        return _done(Status.POLICY_VIOLATION, _format_error(exc, policy))
    except MemoryError as exc:
        return _done(Status.MEMORY, _format_error(exc, policy))
    except SystemExit as exc:
        code_ = exc.code
        exit_code = (
            0 if code_ is None else code_ if isinstance(code_, int) else 1
        )
        return p.Done(
            status=Status.OK.value, control="system_exit", exit_code=exit_code
        )
    except KeyboardInterrupt:
        return p.Done(status=Status.OK.value, control="keyboard_interrupt")
    except BaseException as exc:  # user code: report everything else
        return _done(Status.ERROR, _format_error(exc, policy))
    return _done(Status.OK)


def main(parent_pid: int) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ctrl+C is the host's job
    sys.dont_write_bytecode = True
    chan = _Channel()

    init = chan.receive()
    if not isinstance(init, p.Init):
        os._exit(2)
    cfg = SandboxConfig(**init.config)
    policy: Policy = SandboxPolicy(cfg)
    ns = _build_namespace(chan, policy, init.tool_names)
    out = _StreamToParent(chan, "stdout")
    err = _StreamToParent(chan, "stderr")

    policy.lock_down()  # irreversible restrictions go here, before Ready
    chan.send(p.Ready())

    for n in itertools.count(1):
        msg = chan.receive()
        if not isinstance(msg, p.Exec):
            os._exit(2)
        with redirect_stdout(out), redirect_stderr(err):
            done = _run(msg.code, ns, policy, f"<sandbox-{n}>")
        chan.send(done)

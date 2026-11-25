"""Parent side: owns the worker process, enforces the wall-clock timeout,
relays tool calls, and turns messages into an ExecResult."""

from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from types import TracebackType
from typing import IO, Any

from . import protocol as p
from .config import SandboxConfig
from .result import ExecResult, Status, truncate

ToolHandler = Callable[..., Any]

STARTUP_TIMEOUT_S = 15.0
CLOSE_GRACE_S = 1.0
_SRC_ROOT = str(Path(__file__).resolve().parents[2])  # .../src
_BOOTSTRAP = (
    "import sys; sys.path.insert(0, sys.argv[1]); "
    "from agent_smith.sandbox.worker import main; "
    "main(int(sys.argv[2]))"
)


class _Deadline(Exception):
    pass


class _LineReader:
    """Reads whole lines from a pipe fd, with a deadline.

    os.read + select on the raw fd: a buffered file object could hold a line
    in its buffer while select() says "nothing to read"."""

    def __init__(self, fd: int) -> None:
        self.fd = fd
        self.buf = bytearray()

    def read_line(self, deadline: float) -> bytes | None:
        while True:
            nl = self.buf.find(b"\n")
            if nl >= 0:
                line = bytes(self.buf[: nl + 1])
                del self.buf[: nl + 1]
                return line
            if len(self.buf) > p.MAX_LINE_BYTES:
                raise p.ProtocolError("message too long")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _Deadline
            ready, _, _ = select.select([self.fd], [], [], remaining)
            if not ready:
                continue
            chunk = os.read(self.fd, 65536)
            if not chunk:
                return None
            self.buf += chunk


class _OutputBuffer:
    """Keeps the first and last 'limit // 2' characters, counts the rest,
    so a flood of output never uses more than 'limit' memory."""

    def __init__(self, limit: int) -> None:
        self.half = limit // 2
        self.head = ""
        self.tail = ""
        self.total = 0

    def add(self, data: str) -> None:
        self.total += len(data)
        if len(self.head) < self.half:
            take = self.half - len(self.head)
            self.head += data[:take]
            data = data[take:]
        if data:
            self.tail = (self.tail + data)[-self.half:]

    def text(self) -> tuple[str, bool]:
        kept = len(self.head) + len(self.tail)
        if self.total <= kept:
            return self.head + self.tail, False
        cut = self.total - kept
        return (
            f"{self.head}\n...[{cut}] characters truncated]...\n{self.tail}"
        ), True


class Sandbox:
    """A persistent sandbox session (one worker process).

    with Sandbox(config, tools) as sbx:
        result = sbx.run("x = 1")
        result = sbx.run("print(x)")
    """

    def __init__(
        self,
        config: SandboxConfig | None = None,
        tools: Mapping[str, ToolHandler] | None = None,
    ) -> None:
        self.config = config or SandboxConfig()
        self.tools = dict(tools or {})
        self._proc: subprocess.Popen[bytes] | None = None
        self._reader: _LineReader | None = None
        self._errlog: IO[bytes] | None = None

    # -------------------------------------------------------------- lifecycle

    def __enter__(self) -> Sandbox:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _cwd(self) -> str | None:
        for d in self.config.allowed_directories:
            if os.path.isdir(d):
                return d
        return None

    def _start(self) -> None:
        self._errlog = tempfile.TemporaryFile()

        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-c",
                _BOOTSTRAP,
                _SRC_ROOT,
                str(os.getpid()),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._errlog,
            cwd=self._cwd(),
            env={"PATH": os.defpath, "LC_ALL": "C.UTF-8"},
        )

        assert self._proc.stdout is not None
        self._reader = _LineReader(self._proc.stdout.fileno())
        self._send(
            p.Init(
                config=self.config.model_dump(), tool_names=sorted(self.tools)
            )
        )
        try:
            msg = self._receive(time.monotonic() + STARTUP_TIMEOUT_S)
        except _Deadline:
            raise p.ProtocolError("worker did not start in time") from None
        if not isinstance(msg, p.Ready):
            raise p.ProtocolError(f"expected ready, got {msg!r}")

    def kill(self) -> None:
        """Stop the worker now. Safe to call at any time."""
        proc, self._proc = self._proc, None
        if proc is not None:
            if proc.poll() is None:
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            proc.wait()
            for pipe in (proc.stdin, proc.stdout):
                if pipe:
                    pipe.close()
        if self._errlog:
            self._errlog.close()
            self._errlog = None
        self._reader = None

    def close(self) -> None:
        """Ask the worker to exit (EOF on its input), then kill it."""
        proc = self._proc
        if proc is not None and proc.stdin:
            try:
                proc.stdin.close()
                proc.wait(timeout=CLOSE_GRACE_S)
            except (OSError, subprocess.TimeoutExpired):
                pass
        self.kill()

    # ---------------------------------------------------------- messaging

    def _send(self, msg: Any) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        p.send(self._proc.stdin, msg)

    def _receive(self, deadline: float) -> Any | None:
        assert self._reader is not None
        line = self._reader.read_line(deadline)
        return None if line is None else p.decode_from_child(line)

    def _stderr_tail(self, size: int = 2000) -> str:
        if not self._errlog:
            return ""
        self._errlog.seek(0, os.SEEK_END)
        self._errlog.seek(max(0, self._errlog.tell() - size))
        return self._errlog.read().decode("utf-8", "replace").strip()

    def _call_tool(self, msg: p.ToolCall) -> p.ToolResult:
        fn = self.tools.get(msg.name)
        if fn is None:
            return p.ToolResult(
                call_id=msg.call_id,
                ok=False,
                value=f"unknown tool '{msg.name}'",
            )
        try:
            value = fn(**msg.kwargs)
        except Exception as exc:
            return p.ToolResult(
                call_id=msg.call_id,
                ok=False,
                value=f"{type(exc).__name__}: {exc}",
            )
        text, _ = truncate(
            value if isinstance(value, str) else str(value),
            self.config.max_output_chars,
        )
        return p.ToolResult(call_id=msg.call_id, ok=True, value=text)

    # ---------------------------------------------------------------- run

    def run(self, code: str) -> ExecResult:
        """Execute code in the persistent namespace. Never raises,
        except SystemExit / KeyboardInterrupt (they belong to the caller).
        """
        out = _OutputBuffer(self.config.max_output_chars)
        err = _OutputBuffer(self.config.max_output_chars)
        final: str | None = None
        started = time.monotonic()
        tool_time = 0.0

        def result(
            status: Status, error: str | None = None, reset: bool = False
        ) -> ExecResult:
            stdout, t1 = out.text()
            stderr, t2 = err.text()
            return ExecResult(
                status=status,
                stdout=stdout,
                stderr=stderr,
                error=error,
                final_answer=final,
                truncated=t1 or t2,
                namespace_reset=reset,
                duration_s=time.monotonic() - started - tool_time,
            )

        try:
            if self._proc is None:
                self._start()
            self._send(p.Exec(code=code))
            deadline = (
                time.monotonic() + self.config.max_execution_time_seconds
            )
            while True:
                msg = self._receive(deadline)
                if msg is None:
                    raise EOFError
                if isinstance(msg, p.Output):
                    (out if msg.stream == "stdout" else err).add(msg.data)
                elif isinstance(msg, p.FinalAnswer):
                    final = msg.value
                elif isinstance(msg, p.ToolCall):
                    t0 = time.monotonic()
                    reply = self._call_tool(msg)
                    spent = time.monotonic() - t0
                    tool_time += spent
                    deadline += spent
                    self._send(reply)
                elif isinstance(msg, p.Done):
                    break
                else:
                    raise p.ProtocolError(f"unexpected {msg.type!r}")
        except _Deadline:
            self.kill()
            return result(Status.TIMEOUT, reset=True)
        except (EOFError, BrokenPipeError):
            log = self._stderr_tail()
            self.kill()
            return result(
                Status.CRASHED,
                reset=True,
                error=(
                    "The sandbox process exited unexpectedly."
                    + (f"\n{log}" if log else "")
                ),
            )
        except p.ProtocolError as exc:
            log = self._stderr_tail()
            self.kill()
            return result(
                Status.CRASHED,
                reset=True,
                error=(
                    f"Sandbox protocol error: {exc}"
                    + (f"\n{log}" if log else "")
                ),
            )
        except BaseException:  # Ctrl+C, SystemExit...
            self.kill()
            raise

        if msg.control == "system_exit":
            raise SystemExit(msg.exit_code)
        if msg.control == "keyboard_interrupt":
            raise KeyboardInterrupt
        try:
            status = Status(msg.status)
        except ValueError:
            status = Status.CRASHED
        return result(status, error=msg.error)


def execute(
    code: str,
    config: SandboxConfig | None = None,
    tools: Mapping[str, ToolHandler] | None = None,
) -> ExecResult:
    """One-shot run in a fresh worker (no state kept)."""
    with Sandbox(config, tools) as sbx:
        return sbx.run(code)

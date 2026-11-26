"""Audit hook: refuses dangerous operations inside the worker (PEP 578).

Python calls the hook before each audited operation (open, socket,
os.system, compile...). Raising cancels it, whatever object or module
the code used to get there. Installed once by SandboxPolicy.lock_down.
"""

from __future__ import annotations

import ast
import os
import sysconfig
from collections.abc import Callable
from typing import Any

from ..data import (
    AUDIT_DENIED_EVENTS,
    AUDIT_READ_EVENTS,
    AUDIT_WRITE_EVENTS,
    SANDBOX_FILENAME_PREFIX,
)
from agent_smith.sandbox.errors import ForbiddenOperation, ForbiddenPath
from agent_smith.sandbox.paths import is_path_allowed

_CHECK_FILENAME = SANDBOX_FILENAME_PREFIX + "policy>"
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC


def python_dirs() -> tuple[str, ...]:
    """Folders the interpreter reads modules from (stdlib, site-packages)."""
    paths = sysconfig.get_paths()
    keys = ("stdlib", "platstdlib", "purelib", "platlib")
    return tuple(sorted({os.path.realpath(paths[k]) for k in keys}))


def _is_write(mode: str | None, flags: int | None) -> bool:
    """open() gives a mode ('w', 'a+'...), os.open() only flags."""
    if mode is not None and any(c in mode for c in "wax+"):
        return True
    return bool((flags or 0) & _WRITE_FLAGS)


class AuditHook:
    """The function given to sys.addaudithook.

    It keeps no state that changes: nothing user code could switch off.
    """

    def __init__(
        self,
        allowed_dirs: list[str],
        check_code: Callable[[ast.Module], list[str]],
    ) -> None:
        self._write_dirs = tuple(allowed_dirs)
        self._python_dirs = python_dirs()
        self._read_dirs = self._write_dirs + self._python_dirs
        self._check_code = check_code

    def __call__(self, event: str, args: tuple[Any, ...]) -> None:
        if event.startswith(AUDIT_DENIED_EVENTS):
            raise ForbiddenOperation(
                f"operation '{event}' is not allowed in the sandbox"
            )
        if event == "open":
            self._check_open(*args)
        elif event in AUDIT_READ_EVENTS:
            self._check_path(event, args[0], self._read_dirs)
        elif event in AUDIT_WRITE_EVENTS:
            self._check_path(event, args[0], self._write_dirs)
            if event in ("os.rename", "os.link", "os.symlink"):
                self._check_path(event, args[1], self._write_dirs)
        elif event == "compile":
            self._check_compile(args[0], args[1])

    def _check_open(self, path: Any, mode: str | None, flags: int) -> None:
        if isinstance(path, int):  # fd 3/4 are the protocol pipes
            raise ForbiddenPath("open() on a file descriptor is denied")
        writing = _is_write(mode, flags)
        dirs = self._write_dirs if writing else self._read_dirs
        self._check_path("open", path, dirs)

    def _check_path(
        self, event: str, path: Any, dirs: tuple[str, ...]
    ) -> None:
        if path is None or isinstance(path, int):
            return  # cwd or an fd: obtained through an audited open
        if not is_path_allowed(path, dirs):
            raise ForbiddenPath(f"{event}: '{os.fsdecode(path)}' is denied")

    def _check_compile(self, source: Any, filename: Any) -> None:
        """Code compiled from a string must pass the same AST policy."""
        if not isinstance(source, (str, bytes)):
            return  # an AST: the worker compiles the tree it checked
        if not isinstance(filename, str):
            filename = os.fsdecode(filename)
        if filename.startswith(SANDBOX_FILENAME_PREFIX):
            return  # the worker's parse (checked next) or ours below
        if is_path_allowed(filename, self._python_dirs):
            return  # a standard library module being imported
        try:
            tree = ast.parse(source, _CHECK_FILENAME)
        except SyntaxError:
            return  # compile() itself will raise it
        problems = self._check_code(tree)
        if problems:
            raise ForbiddenOperation(
                "code compiled at runtime was rejected: " + problems[0]
            )

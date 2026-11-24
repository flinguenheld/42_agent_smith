"""Security policy applied inside the worker. Standard library only.

The worker only talks to SandboxPolicy through four hooks (see the
Policy protocol in worker.py). Each rule of the subject lives in one
of them:

    check(tree) static, before running  -> imports
    builtins()  what user code can call -> safe __import__
    lock_down() irreversible, once      -> rlimits, audit hook
    trusted()   worker-internal operations  -> pauses the audit hook
"""

from __future__ import annotations

import ast
import builtins as _builtins
import contextlib
from collections.abc import Callable, Iterable, Iterator
from typing import Any

from .config import SandboxConfig

# --------------------------------------------------------------------- errors


class SandboxViolation(Exception):
    """Base class: the sandboxed code tries something forbidden."""


class ForbiddenImport(SandboxViolation, ImportError):
    """Also an ImportError, so `try: import x / except ImportError:` works."""


class ForbiddenAttribute(SandboxViolation, AttributeError):
    pass


class ForbiddenPath(SandboxViolation, PermissionError):
    pass


class ForbiddenOperation(SandboxViolation, RuntimeError):
    pass


# -------------------------------------------------------------------- imports


def is_import_allowed(name: str, allowlist: Iterable[str]) -> bool:
    """'a.b' is allowed by 'a.b' or by 'a.*'. 'a.*' does not allow 'a'."""
    for entry in allowlist:
        if entry == name:
            return True
        if entry.endswith(".*") and name.startswith(entry[:-1]):
            return True
    return False


def check_import(
    name: str,
    fromlist: Iterable[str],
    level: int,
    allowlist: list[str],
) -> str | None:
    """One rule for both the static check and the runtime hook.

    Returns None if the import is allowed, otherwise a readble reason.
    """
    fromlist = tuple(fromlist)
    if level:
        return "relative imports are not allowed"
    if "*" in fromlist:
        return "'from ... import *' is not allowed"
    if not is_import_allowed(name, allowlist):
        return (
            f"import of '{name}' is not allowed "
            f"(allowed: {', '.join(allowlist)})"
        )
    top = name.partition(".")[0]
    if not fromlist and top != name and not is_import_allowed(top, allowlist):
        parent, _, child = name.rpartition(".")
        return (
            f"'import {name}' would give access to '{top}', which is not "
            f"allowed; use 'from {parent} import {child}' instead"
        )
    return None


def make_import(allowlist: list[str]) -> Callable[..., Any]:
    """Build the __import__ that user code gets in its builtins."""
    real_import = _builtins.__import__

    def safe_import(
        name: str,
        globals: Any = None,
        locals: Any = None,
        fromlist: Any = (),
        level: int = 0,
    ) -> Any:
        reason = check_import(name, fromlist or (), level, allowlist)
        if reason:
            raise ForbiddenImport(reason)
        return real_import(name, globals, locals, fromlist, level)

    return safe_import


# ----------------------------------------------------------------- static AST


class _Checker(ast.NodeVisitor):
    """Walks the whole tree and collects problems (step 3 adds rules)."""

    def __init__(self, allowlist: list[str]) -> None:
        self.allowlist = allowlist
        self.problems: list[str] = []

    def _bad(self, node: ast.AST, msg: str) -> None:
        self.problems.append(f"line {getattr(node, 'lineno', '?')}: {msg}")

    def visit_ast_import(self, node: ast.Import) -> None:
        for alias in node.names:
            reason = check_import(alias.name, (), 0, self.allowlist)
            if reason:
                self._bad(node, reason)

    def visit_ast_import_from(self, node: ast.ImportFrom) -> None:
        names = [alias.name for alias in node.names]
        reason = check_import(
            node.module or "", names, node.level, self.allowlist
        )
        if reason:
            self._bad(node, reason)


def check_ast(tree: ast.AST, allowlist: list[str]) -> list[str]:
    """Return a list of problems, an empty list means accepted."""
    checker = _Checker(allowlist)
    checker.visit(tree)
    return checker.problems


# --------------------------------------------------------------------- policy


class SandboxPolicy:
    """The policy the worker uses. Implements worker.Policy."""

    violations: tuple[type[BaseException], ...] = (SandboxViolation,)

    def __init__(self, cfg: SandboxConfig) -> None:
        self.cfg = cfg

    def check(self, tree: ast.Module) -> list[str]:
        return check_ast(tree, self.cfg.authorized_imports)

    def builtins(self) -> dict[str, Any]:
        safe = dict(vars(_builtins))
        safe["__import__"] = make_import(self.cfg.authorized_imports)
        return safe

    def lock_down(self) -> None:
        pass

    @contextlib.contextmanager
    def trusted(self) -> Iterator[None]:
        yield

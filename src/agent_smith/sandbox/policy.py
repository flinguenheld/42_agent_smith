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
import os
import sys
from collections.abc import Callable, Iterable, Iterator
from types import ModuleType
from typing import Any, NoReturn

from agent_smith.data import (
    BLOCKED_BUILTINS,
    DENIED_MODULE_ATTRS,
    FORBIDDEN_ATTRS,
    HIDDEN_BUILTINS,
    SAFE_DUNDERS,
)

from agent_smith.sandbox.errors import (
    SandboxViolation,
    ForbiddenImport,
    ForbiddenAttribute,
    ForbiddenPath,
    ForbiddenOperation,
)

from agent_smith.sandbox.config import SandboxConfig
from agent_smith.sandbox.paths import is_path_allowed, real_path
from agent_smith.sandbox.limits import apply_limits
from agent_smith.sandbox.audit import AuditHook


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


def module_view(
    mod: ModuleType, allowlist: list[str], cache: dict[str, ModuleType]
) -> ModuleType:
    """A new module holding only the safe names of mod.

    Like safe_builtins: the real module is left untouched, user code gets
    a filtered copy. Skipped: private names (random._os) and modules not
    on the allowlist (typing.sys). DENIED_MODULE_ATTRS become stubs.
    Allowed sub-modules (collections.abc) are views too.
    """
    if mod.__name__ in cache:
        return cache[mod.__name__]
    view = ModuleType(mod.__name__, mod.__doc__)
    cache[mod.__name__] = view
    denied = DENIED_MODULE_ATTRS.get(mod.__name__, frozenset())
    for name, value in vars(mod).items():
        if name.startswith("_"):
            continue
        if name in denied:
            value = _blocked(f"{mod.__name__}.{name}")
        elif isinstance(value, ModuleType):
            if not is_import_allowed(value.__name__, allowlist):
                continue
            value = module_view(value, allowlist, cache)
        setattr(view, name, value)
    return view


def _check_fromlist(
    view: ModuleType, real: ModuleType, fromlist: Iterable[str]
) -> None:
    """`from m import a, b`: fail now if a or b is not in the view.

    Otherwise Python retries with sys.modules["m.a"] and hands out the
    real, unfiltered module.
    """
    for attr in fromlist:
        if hasattr(view, attr):
            continue
        if hasattr(real, attr):
            raise ForbiddenImport(f"'{real.__name__}.{attr}' is not allowed")
        raise ImportError(
            f"cannot import name '{attr}' from '{real.__name__}'"
        )


def make_import(allowlist: list[str]) -> Callable[..., Any]:
    """Build the __import__ that user code gets in its builtins."""
    real_import = _builtins.__import__
    cache: dict[str, ModuleType] = {}

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
        real = real_import(name, globals, locals, fromlist, level)
        view = module_view(real, allowlist, cache)
        _check_fromlist(view, real, fromlist or ())
        return view

    return safe_import


# ------------------------------------------------------------------- builtins


def is_dunder(name: str) -> bool:
    """True for dunders, names like __class__"""
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


def is_attr_allowed(name: str) -> bool:
    """False for dunders (except SAFE_DUNDERS) and for FORBIDDEN_ATTRS."""
    if is_dunder(name):
        return name in SAFE_DUNDERS
    return name not in FORBIDDEN_ATTRS


def attr_error(name: str) -> str:
    """The message for a refused attribute (static and runtime checks)"""
    return f"access to attribute '{name}' is not allowed"


def _checked(name: Any) -> str:
    """Return name if user code may use it as an attribute, else raise."""
    if not isinstance(name, str):
        raise TypeError("attribute name must be a string")
    if not is_attr_allowed(name):
        raise ForbiddenAttribute(attr_error(name))
    return name


def safe_getattr(obj: Any, name: Any, *default: Any) -> Any:
    """getattr() that refuses the attributes is_attr_allowed() refuses."""
    return getattr(obj, _checked(name), *default)


def safe_setattr(obj: Any, name: Any, value: Any) -> None:
    """setattr() that refuses the attributes is_attr_allowed() refuses."""
    setattr(obj, _checked(name), value)


def safe_delattr(obj: Any, name: Any) -> None:
    """delattr() that refuses the attributes is_attr_allowed() refuses."""
    delattr(obj, _checked(name))


def _blocked(name: str) -> Callable[..., NoReturn]:
    """A stand-in for a removed builtin, with an explicit error."""

    def blocked(*args: Any, **kwargs: Any) -> NoReturn:
        raise ForbiddenOperation(f"{name}() is not available in the sandbox")

    blocked.__name__ = blocked.__qualname__ = name
    return blocked


def make_open(allowed_dirs: list[str]) -> Callable[..., Any]:
    """Build the open() that user code gets: allowed directories only."""
    real_open = _builtins.open

    def safe_open(
        file: Any, mode: str = "r", *args: Any, **kwargs: Any
    ) -> Any:
        if not isinstance(file, (str, bytes, os.PathLike)):
            raise ForbiddenPath("open() only accepts a path")
        if "opener" in kwargs or len(args) >= 6:
            raise ForbiddenPath("open(opener=...) is not allowed")
        path = real_path(file)
        if not is_path_allowed(path, allowed_dirs):
            raise ForbiddenPath(
                f"access to '{path}' is denied "
                f"(allowed directories: {', '.join(allowed_dirs)})"
            )
        return real_open(path, mode, *args, **kwargs)

    return safe_open


def safe_builtins(cfg: SandboxConfig) -> dict[str, Any]:
    """The __builtins__ dict given to user code."""
    safe = {
        k: v for k, v in vars(_builtins).items() if k not in HIDDEN_BUILTINS
    }
    safe.update({name: _blocked(name) for name in BLOCKED_BUILTINS})
    safe.update(
        {
            "__import__": make_import(cfg.authorized_imports),
            "open": make_open(cfg.allowed_directories),
            "getattr": safe_getattr,
            "setattr": safe_setattr,
            "delattr": safe_delattr,
        }
    )
    return safe


# ----------------------------------------------------------------- static AST


class _Checker(ast.NodeVisitor):
    """Walks the whole tree and collects problems (step 3 adds rules)."""

    def __init__(self, allowlist: list[str]) -> None:
        self.allowlist = allowlist
        self.problems: list[str] = []

    def _bad(self, node: ast.AST, msg: str) -> None:
        self.problems.append(f"line {getattr(node, 'lineno', '?')}: {msg}")

    def _check_names(self, node: ast.AST, name: str | None) -> None:
        """Refuse dunder vairable names, except SAFE_DUNDERS."""
        if name and is_dunder(name) and name not in SAFE_DUNDERS:
            self._bad(node, f"name '{name}' is not allowed")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            reason = check_import(alias.name, (), 0, self.allowlist)
            if reason:
                self._bad(node, reason)
            self._check_names(node, alias.asname)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        names = [alias.name for alias in node.names]
        reason = check_import(
            node.module or "", names, node.level, self.allowlist
        )
        if reason:
            self._bad(node, reason)
        for alias in node.names:
            self._check_names(node, alias.asname)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # attribute access, like `obj.name`
        if not is_attr_allowed(node.attr):
            self._bad(node, attr_error(node.attr))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self._check_names(node, node.id)

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            self._check_names(node, name)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        # variables in closest outer scope
        for name in node.names:
            self._check_names(node, name)

    def visit_MatchClass(self, node: ast.MatchClass) -> None:
        # `case C(attr=x)` reads C.attr without any Attribute node
        for attr in node.kwd_attrs:
            if not is_attr_allowed(attr):
                self._bad(node, attr_error(attr))
        self.generic_visit(node)


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
        return safe_builtins(self.cfg)

    def lock_down(self) -> None:
        apply_limits(self.cfg.max_memory_mb)
        sys.addaudithook(AuditHook(self.cfg.allowed_directories, self.check))

    @contextlib.contextmanager
    def trusted(self) -> Iterator[None]:
        yield

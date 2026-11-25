"""Exceptions raised when sandboxed code tries something forbidden.

Each one also inherits the built-in error a normal program would get,
so ordinary `except ImportError:` or `except OSError:` code still works.
"""


class SandboxViolation(Exception):
    """Base class: the sandboxed code tries something forbidden."""


class ForbiddenImport(SandboxViolation, ImportError):
    """Also an ImportError, so `try: import x / except ImportError:` works."""


class ForbiddenAttribute(SandboxViolation, AttributeError):
    """An attribute (dunder, frame...) user code may not use."""


class ForbiddenPath(SandboxViolation, PermissionError):
    """A file or directory outside the allowed directories."""


class ForbiddenOperation(SandboxViolation, RuntimeError):
    """A builtin or an operation (process, socket...) that is refused."""

"""Path rules shared by the safe open() and the audit hook."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Union

PathLike = Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"]


def real_path(path: PathLike) -> str:
    """Absolute path with '..' and symlinks resolved."""
    return os.path.realpath(os.fsdecode(path))


def is_path_allowed(path: PathLike, allowed_dirs: Iterable[str]) -> bool:
    """True if path is inside one of allowed_dirs (themselves real paths).

    commonpath compares whole components: /testbed2 is not in /testbed,
    which a plain startswith() would accept.
    """

    real = real_path(path)
    return any(os.path.commonpath([real, d]) == d for d in allowed_dirs)

"""OS resources limits of the worker process (setrlimit)."""

from __future__ import annotations

import resource
import signal

from agent_smith.data import MAX_FILE_BYTES, MAX_OPEN_FILES


def _lower(limit: int, value: int) -> None:
    """Set soft and hard to value: the process can never raise them back.

    An already lower hard limit is kept: setrlimit can't raise it.
    """

    _, hard = resource.getrlimit(limit)
    if hard != resource.RLIM_INFINITY:
        value = min(value, hard)
    resource.setrlimit(limit, (value, value))


def apply_limits(max_memory_mb: int) -> None:
    """Lower the worker's limits. Irreversible: call it once, last."""
    _lower(resource.RLIMIT_AS, max_memory_mb * 1024 * 1024)
    _lower(resource.RLIMIT_NPROC, 0)  # no child processes
    _lower(resource.RLIMIT_FSIZE, MAX_FILE_BYTES)
    _lower(resource.RLIMIT_NOFILE, MAX_OPEN_FILES)
    _lower(resource.RLIMIT_CORE, 0)  # no core dump files
    # over FSIZE, the kerner sends SIGXFSZ, which kills the process by default
    # ignored, the write fails with OSError instead
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)

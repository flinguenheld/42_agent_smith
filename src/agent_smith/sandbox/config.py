from __future__ import annotations

import os
import re
from pathlib import Path

from typing import List
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    ValidationError,
    field_validator,
)

_IMPORT_ENTRY = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*(\.\*)?$")


class SandboxConfigError(Exception):
    """Raised when a config file cannot be read or is invalid"""


class SandboxConfig(BaseModel):
    """Sandbox configuration for student solutions.
    Uses allowlist approach: only imports in authorized_imports are allowed.
    Everything else is blocked by default.
    """

    model_config = ConfigDict(frozen=True)

    authorized_imports: List[str] = Field(
        default_factory=lambda: [
            "math",
            "math.*",
            "collections",
            "collections.*",
            "itertools",
            "re",
            "json",
            "typing",
            "typing.*",
            "functools",
            "operator",
            "heapq",
            "bisect",
            "copy",
            "string",
            "random",
            "datetime",
            "datetime.*",
            "array",
            "cmath",
        ]
    )
    allowed_directories: List[str] = Field(
        default_factory=lambda: ["/testbed", "/tmp/agent"]
    )
    max_execution_time_seconds: int = Field(default=30, gt=0)
    max_memory_mb: int = Field(default=512, gt=0)
    max_output_chars: int = Field(default=20_000, gt=0)

    @field_validator("authorized_imports")
    @classmethod
    def _check_imports(cls, entries: list[str]) -> list[str]:
        bad = [e for e in entries if not _IMPORT_ENTRY.match(e)]
        if bad:
            raise ValueError(f"invalid import entries: {bad}")
        return entries

    @field_validator("allowed_directories")
    @classmethod
    def _normalize_dirs(cls, dirs: list[str]) -> list[str]:
        out = []
        for d in dirs:
            if not os.path.isabs(d):
                raise ValueError(f"directory must be absolute: {d!r}")
            out.append(os.path.realpath(d))
        return out

    @classmethod
    def from_json_file(cls, path: str | os.PathLike[str]) -> SandboxConfig:
        """Load and validate a JSON config file, with a readable error."""
        try:
            return cls.model_validate_json(Path(path).read_text("utf-8"))
        except OSError as exc:
            raise SandboxConfigError(f"cannot read {path}: {exc}") from exc
        except ValidationError as exc:
            raise SandboxConfigError(f"invalid config {path}:\n{exc}") from exc

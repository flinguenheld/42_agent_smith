"""Fixtures shared by the sandbox tests."""

import pytest

from agent_smith.sandbox import SandboxConfig

# Modules a careless config could allow: the audit hook must hold alone.
LEAKY_IMPORTS = ["os", "socket", "subprocess", "shutil", "inspect"]


@pytest.fixture
def workspace(tmp_path):
    """testbed/ (with a.txt), agent/, and a secret file outside both."""
    (tmp_path / "testbed").mkdir()
    (tmp_path / "agent").mkdir()
    (tmp_path / "testbed" / "a.txt").write_text("hello\n")
    (tmp_path / "outside.txt").write_text("secret\n")
    (tmp_path / "testbed" / "link.txt").symlink_to(tmp_path / "outside.txt")
    return tmp_path


@pytest.fixture
def secure_cfg(workspace):
    """The default allowlist, with the two workspace directories."""
    return SandboxConfig(
        allowed_directories=[
            str(workspace / "testbed"),
            str(workspace / "agent"),
        ],
        max_execution_time_seconds=5,
        max_memory_mb=256,
    )


@pytest.fixture
def leaky_cfg(secure_cfg):
    """secure_cfg plus dangerous modules: tests the audit hook alone."""
    imports = secure_cfg.authorized_imports + LEAKY_IMPORTS
    return secure_cfg.model_copy(update={"authorized_imports": imports})

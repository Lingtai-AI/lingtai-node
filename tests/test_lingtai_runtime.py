"""Tests for the LingTai kernel runtime adapter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lingtai_node.contracts import RUNTIME_FILE_MAP, runtime_exists
from lingtai_node.runtimes.lingtai import LingTaiRuntime


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def lingtai_node_dir(tmp_node_dir_factory) -> Path:
    """Create a valid lingtai runtime node directory."""
    return tmp_node_dir_factory(name="lingtai-agent", runtime="lingtai")


@pytest.fixture
def runtime(lingtai_node_dir: Path) -> LingTaiRuntime:
    """Create a LingTaiRuntime bound to a valid node directory."""
    return LingTaiRuntime(lingtai_node_dir)


@pytest.fixture
def empty_runtime(tmp_path: Path) -> LingTaiRuntime:
    """Create a LingTaiRuntime bound to an empty directory."""
    d = tmp_path / "empty-agent"
    d.mkdir()
    return LingTaiRuntime(d)


# ------------------------------------------------------------------
# runtime_exists()
# ------------------------------------------------------------------

def test_runtime_exists_lingtai():
    """The 'lingtai' runtime must be registered."""
    assert runtime_exists("lingtai") is True


def test_runtime_exists_known_runtimes():
    """All known runtimes should return True."""
    for name in RUNTIME_FILE_MAP:
        assert runtime_exists(name) is True


def test_runtime_exists_unknown():
    """Unknown runtime names should return False."""
    assert runtime_exists("nonexistent-runtime") is False
    assert runtime_exists("") is False


# ------------------------------------------------------------------
# Validation — valid directory
# ------------------------------------------------------------------

def test_validate_valid_directory(runtime: LingTaiRuntime):
    """A fully populated lingtai directory should validate."""
    result = runtime.validate()
    assert result["valid"] is True, f"Errors: {result['errors']}"
    assert result["errors"] == []


# ------------------------------------------------------------------
# Validation — missing artifacts
# ------------------------------------------------------------------

def test_validate_empty_directory(empty_runtime: LingTaiRuntime):
    """An empty directory fails validation."""
    result = empty_runtime.validate()
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_validate_missing_identity(lingtai_node_dir: Path):
    """Missing lingtai.md is a validation error."""
    (lingtai_node_dir / "lingtai.md").unlink()
    rt = LingTaiRuntime(lingtai_node_dir)
    result = rt.validate()
    assert result["valid"] is False
    assert any("lingtai.md" in e for e in result["errors"])


def test_validate_missing_mailbox(lingtai_node_dir: Path):
    """Missing mailbox/ is a validation error."""
    import shutil
    shutil.rmtree(lingtai_node_dir / "mailbox")
    rt = LingTaiRuntime(lingtai_node_dir)
    result = rt.validate()
    assert result["valid"] is False
    assert any("mailbox" in e for e in result["errors"])


def test_validate_missing_memory_is_warning(lingtai_node_dir: Path):
    """Missing pad.md is a warning, not an error."""
    (lingtai_node_dir / "pad.md").unlink()
    rt = LingTaiRuntime(lingtai_node_dir)
    result = rt.validate()
    assert result["valid"] is True
    assert any("pad.md" in w for w in result["warnings"])


def test_validate_missing_handover_dir_is_warning(lingtai_node_dir: Path):
    """Missing system/summaries/ is a warning."""
    import shutil
    shutil.rmtree(lingtai_node_dir / "system")
    rt = LingTaiRuntime(lingtai_node_dir)
    result = rt.validate()
    assert result["valid"] is True
    assert any("system/summaries" in w for w in result["warnings"])


# ------------------------------------------------------------------
# Artifact accessors — identity
# ------------------------------------------------------------------

def test_get_identity_reads_file(runtime: LingTaiRuntime):
    """get_identity() returns the contents of lingtai.md."""
    content = runtime.get_identity()
    assert "# Identity for lingtai" in content


def test_get_identity_missing_returns_empty(empty_runtime: LingTaiRuntime):
    """get_identity() returns '' when the file does not exist."""
    assert empty_runtime.get_identity() == ""


# ------------------------------------------------------------------
# Artifact accessors — memory
# ------------------------------------------------------------------

def test_get_memory_reads_file(runtime: LingTaiRuntime):
    """get_memory() returns the contents of pad.md."""
    content = runtime.get_memory()
    assert "# Memory for lingtai" in content


def test_get_memory_missing_returns_empty(empty_runtime: LingTaiRuntime):
    """get_memory() returns '' when the file does not exist."""
    assert empty_runtime.get_memory() == ""


# ------------------------------------------------------------------
# Artifact accessors — directories
# ------------------------------------------------------------------

def test_get_knowledge_dir_exists(runtime: LingTaiRuntime):
    """get_knowledge_dir() returns codex/ and it exists."""
    kdir = runtime.get_knowledge_dir()
    assert kdir.is_dir()
    assert kdir.name == "codex"


def test_get_knowledge_dir_creates_if_missing(empty_runtime: LingTaiRuntime):
    """get_knowledge_dir() creates codex/ if absent."""
    kdir = empty_runtime.get_knowledge_dir()
    assert kdir.is_dir()
    assert kdir.name == "codex"


def test_get_skills_dir_exists(runtime: LingTaiRuntime):
    """get_skills_dir() returns .library/ and it exists."""
    sdir = runtime.get_skills_dir()
    assert sdir.is_dir()
    assert sdir.name == ".library"


def test_get_skills_dir_creates_if_missing(empty_runtime: LingTaiRuntime):
    """get_skills_dir() creates .library/ if absent."""
    sdir = empty_runtime.get_skills_dir()
    assert sdir.is_dir()
    assert sdir.name == ".library"


def test_get_mailbox_dir_has_subdirs(runtime: LingTaiRuntime):
    """get_mailbox_dir() returns mailbox/ with inbox/, sent/, archive/."""
    mdir = runtime.get_mailbox_dir()
    assert mdir.is_dir()
    assert (mdir / "inbox").is_dir()
    assert (mdir / "sent").is_dir()
    assert (mdir / "archive").is_dir()


def test_get_mailbox_dir_creates_if_missing(empty_runtime: LingTaiRuntime):
    """get_mailbox_dir() creates the full mailbox structure if absent."""
    mdir = empty_runtime.get_mailbox_dir()
    assert mdir.is_dir()
    assert (mdir / "inbox").is_dir()
    assert (mdir / "sent").is_dir()
    assert (mdir / "archive").is_dir()


def test_get_handover_dir_exists(runtime: LingTaiRuntime):
    """get_handover_dir() returns system/summaries/ and it exists."""
    hdir = runtime.get_handover_dir()
    assert hdir.is_dir()
    assert hdir.name == "summaries"
    assert hdir.parent.name == "system"


def test_get_handover_dir_creates_if_missing(empty_runtime: LingTaiRuntime):
    """get_handover_dir() creates system/summaries/ if absent."""
    hdir = empty_runtime.get_handover_dir()
    assert hdir.is_dir()
    assert hdir.name == "summaries"


# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------

def test_get_agent_metadata(runtime: LingTaiRuntime):
    """get_agent_metadata() reads .agent.json."""
    meta = runtime.get_agent_metadata()
    assert meta is not None
    assert meta["name"] == "lingtai-agent"
    assert meta["runtime"] == "lingtai"
    assert meta["contract_version"] == "2.0.0"


def test_get_agent_metadata_missing(empty_runtime: LingTaiRuntime):
    """get_agent_metadata() returns None when .agent.json is absent."""
    assert empty_runtime.get_agent_metadata() is None


def test_get_agent_metadata_corrupt(lingtai_node_dir: Path):
    """get_agent_metadata() returns None when .agent.json is corrupt."""
    (lingtai_node_dir / ".agent.json").write_text("NOT JSON")
    rt = LingTaiRuntime(lingtai_node_dir)
    assert rt.get_agent_metadata() is None


# ------------------------------------------------------------------
# Runtime constants
# ------------------------------------------------------------------

def test_runtime_name_constant():
    """RUNTIME_NAME matches the contract map key."""
    assert LingTaiRuntime.RUNTIME_NAME == "lingtai"
    assert LingTaiRuntime.RUNTIME_NAME in RUNTIME_FILE_MAP


def test_agent_dir_property(runtime: LingTaiRuntime, lingtai_node_dir: Path):
    """agent_dir property returns the path passed to the constructor."""
    assert runtime.agent_dir == lingtai_node_dir

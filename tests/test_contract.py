"""Tests for the Node Contract validator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lingtai_node.contracts import (
    NODE_CONTRACT_VERSION,
    RUNTIME_FILE_MAP,
    validate_node,
)


# ------------------------------------------------------------------
# Valid nodes — one per runtime
# ------------------------------------------------------------------

@pytest.mark.parametrize("runtime", list(RUNTIME_FILE_MAP.keys()))
def test_valid_node_all_runtimes(tmp_node_dir_factory, runtime: str):
    """A fully populated node directory should validate with no errors."""
    node_dir = tmp_node_dir_factory(name=f"node-{runtime}", runtime=runtime)
    result = validate_node(node_dir, runtime=runtime)
    assert result["valid"] is True, f"Errors: {result['errors']}"
    assert result["errors"] == []


@pytest.mark.parametrize("runtime", list(RUNTIME_FILE_MAP.keys()))
def test_valid_node_no_warnings_except_optional(tmp_node_dir_factory, runtime: str):
    """A fully populated node should have no errors; warnings are for optional items only."""
    node_dir = tmp_node_dir_factory(name=f"node-{runtime}", runtime=runtime)
    result = validate_node(node_dir, runtime=runtime)
    assert result["valid"] is True
    # With all files created by the factory, no warnings should fire
    # except possibly handover (which we do create in the factory).
    for w in result["warnings"]:
        # Only acceptable warnings are about optional items
        assert "will be created" in w or "optional" in w.lower(), f"Unexpected warning: {w}"


# ------------------------------------------------------------------
# Missing .agent.json
# ------------------------------------------------------------------

def test_missing_agent_json(tmp_empty_dir: Path):
    """Missing .agent.json is a validation error."""
    result = validate_node(tmp_empty_dir, runtime="claude-code")
    assert result["valid"] is False
    assert any(".agent.json" in e for e in result["errors"])


def test_invalid_agent_json(tmp_node_dir: Path):
    """Corrupt .agent.json is a validation error."""
    (tmp_node_dir / ".agent.json").write_text("NOT JSON", encoding="utf-8")
    result = validate_node(tmp_node_dir, runtime="claude-code")
    assert result["valid"] is False
    assert any(".agent.json is invalid" in e for e in result["errors"])


def test_agent_json_missing_fields(tmp_node_dir: Path):
    """Missing name/runtime fields in .agent.json produce warnings."""
    (tmp_node_dir / ".agent.json").write_text("{}", encoding="utf-8")
    result = validate_node(tmp_node_dir, runtime="claude-code")
    # Missing name and runtime are warnings, not errors
    assert any("'name'" in w for w in result["warnings"])
    assert any("'runtime'" in w for w in result["warnings"])


# ------------------------------------------------------------------
# Missing character file
# ------------------------------------------------------------------

def test_missing_character_file(tmp_node_dir: Path):
    """Missing character file (CLAUDE.md for claude-code) is an error."""
    char_file = RUNTIME_FILE_MAP["claude-code"][0]
    (tmp_node_dir / char_file).unlink()
    result = validate_node(tmp_node_dir, runtime="claude-code")
    assert result["valid"] is False
    assert any(char_file in e for e in result["errors"])


@pytest.mark.parametrize("runtime", list(RUNTIME_FILE_MAP.keys()))
def test_missing_character_file_per_runtime(tmp_node_dir_factory, runtime: str):
    """Missing character file is an error for every runtime."""
    node_dir = tmp_node_dir_factory(name=f"node-{runtime}", runtime=runtime)
    char_file = RUNTIME_FILE_MAP[runtime][0]
    (node_dir / char_file).unlink()
    result = validate_node(node_dir, runtime=runtime)
    assert result["valid"] is False
    assert any(char_file in e for e in result["errors"])


# ------------------------------------------------------------------
# Missing memory file
# ------------------------------------------------------------------

def test_missing_memory_file_is_warning(tmp_node_dir: Path):
    """Missing memory file is a warning, not an error."""
    mem_file = RUNTIME_FILE_MAP["claude-code"][1]
    (tmp_node_dir / mem_file).unlink()
    result = validate_node(tmp_node_dir, runtime="claude-code")
    assert result["valid"] is True  # still valid
    assert any(mem_file in w for w in result["warnings"])


# ------------------------------------------------------------------
# Missing mailbox structure
# ------------------------------------------------------------------

def test_missing_mailbox_dir(tmp_node_dir: Path):
    """Missing mailbox/ directory entirely is an error."""
    import shutil
    shutil.rmtree(tmp_node_dir / "mailbox")
    result = validate_node(tmp_node_dir, runtime="claude-code")
    assert result["valid"] is False
    assert any("mailbox" in e for e in result["errors"])


def test_missing_mailbox_subdirs(tmp_node_dir: Path):
    """Missing mailbox subdirectories (inbox, sent, archive) are errors."""
    import shutil
    shutil.rmtree(tmp_node_dir / "mailbox" / "sent")
    result = validate_node(tmp_node_dir, runtime="claude-code")
    assert result["valid"] is False
    assert any("mailbox/sent" in e for e in result["errors"])


# ------------------------------------------------------------------
# Missing handover file
# ------------------------------------------------------------------

def test_missing_handover_is_warning(tmp_node_dir: Path):
    """Missing handover.md is a warning (created on first compact)."""
    handover_file = RUNTIME_FILE_MAP["claude-code"][3]
    (tmp_node_dir / handover_file).unlink()
    result = validate_node(tmp_node_dir, runtime="claude-code")
    assert result["valid"] is True
    assert any(handover_file in w for w in result["warnings"])


# ------------------------------------------------------------------
# Missing knowledge directory
# ------------------------------------------------------------------

def test_missing_knowledge_dir_is_warning(tmp_node_dir: Path):
    """Missing knowledge directory is a warning (created on first use)."""
    import shutil
    lt_dir = RUNTIME_FILE_MAP["claude-code"][2]
    shutil.rmtree(tmp_node_dir / lt_dir)
    result = validate_node(tmp_node_dir, runtime="claude-code")
    assert result["valid"] is True
    assert any(lt_dir in w for w in result["warnings"])


# ------------------------------------------------------------------
# Non-existent directory
# ------------------------------------------------------------------

def test_nonexistent_directory(tmp_path: Path):
    """Validating a non-existent path returns invalid."""
    result = validate_node(tmp_path / "does-not-exist", runtime="claude-code")
    assert result["valid"] is False
    assert len(result["errors"]) == 1
    assert "does not exist" in result["errors"][0]


# ------------------------------------------------------------------
# Unknown runtime
# ------------------------------------------------------------------

def test_unknown_runtime(tmp_node_dir: Path):
    """Unknown runtime produces a warning about character file check."""
    result = validate_node(tmp_node_dir, runtime="unknown-runtime-xyz")
    assert any("Unknown runtime" in w for w in result["warnings"])


# ------------------------------------------------------------------
# Contract version
# ------------------------------------------------------------------

def test_contract_version_is_2():
    """Contract version should be 2.x."""
    assert NODE_CONTRACT_VERSION.startswith("2.")

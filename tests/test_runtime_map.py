"""Tests for the runtime file map."""
from __future__ import annotations

import pytest

from lingtai_node.contracts import RUNTIME_FILE_MAP


# ------------------------------------------------------------------
# Required runtimes
# ------------------------------------------------------------------

EXPECTED_RUNTIMES = {"claude-code", "openai-codex", "lingtai", "hermes"}


def test_all_runtimes_present():
    """RUNTIME_FILE_MAP must include all four supported runtimes."""
    assert set(RUNTIME_FILE_MAP.keys()) == EXPECTED_RUNTIMES


def test_no_extra_runtimes():
    """No unexpected runtimes in the map."""
    assert set(RUNTIME_FILE_MAP.keys()) == EXPECTED_RUNTIMES


# ------------------------------------------------------------------
# Tuple structure
# ------------------------------------------------------------------

@pytest.mark.parametrize("runtime", EXPECTED_RUNTIMES)
def test_map_value_is_4_tuple(runtime: str):
    """Each entry must be a 4-tuple: (char, mem, knowledge_dir, handover)."""
    entry = RUNTIME_FILE_MAP[runtime]
    assert isinstance(entry, tuple)
    assert len(entry) == 4, f"{runtime}: expected 4-tuple, got {len(entry)}"


@pytest.mark.parametrize("runtime", EXPECTED_RUNTIMES)
def test_all_fields_are_nonempty_strings(runtime: str):
    """All four fields must be non-empty strings."""
    for i, field in enumerate(RUNTIME_FILE_MAP[runtime]):
        assert isinstance(field, str), f"{runtime}[{i}]: expected str, got {type(field)}"
        assert len(field) > 0, f"{runtime}[{i}]: empty string"


# ------------------------------------------------------------------
# File extension correctness
# ------------------------------------------------------------------

@pytest.mark.parametrize("runtime", EXPECTED_RUNTIMES)
def test_character_file_has_md_extension(runtime: str):
    """Character file must end in .md (all runtimes use markdown)."""
    char_file = RUNTIME_FILE_MAP[runtime][0]
    assert char_file.endswith(".md"), f"{runtime}: character file '{char_file}' is not .md"


@pytest.mark.parametrize("runtime", EXPECTED_RUNTIMES)
def test_memory_file_has_md_extension(runtime: str):
    """Memory file must end in .md."""
    mem_file = RUNTIME_FILE_MAP[runtime][1]
    assert mem_file.endswith(".md"), f"{runtime}: memory file '{mem_file}' is not .md"


_FILE_HANDOVER_RUNTIMES = {"claude-code", "openai-codex", "hermes"}


@pytest.mark.parametrize("runtime", _FILE_HANDOVER_RUNTIMES)
def test_file_handover_has_md_extension(runtime: str):
    """Runtimes that use a handover *file* must end in .md."""
    handover = RUNTIME_FILE_MAP[runtime][3]
    assert handover.endswith(".md"), f"{runtime}: handover '{handover}' is not .md"


def test_lingtai_handover_is_directory_path():
    """LingTai uses a handover *directory* (system/summaries), not a file."""
    handover = RUNTIME_FILE_MAP["lingtai"][3]
    assert not handover.endswith(".md")
    assert "/" in handover  # nested directory path


@pytest.mark.parametrize("runtime", EXPECTED_RUNTIMES)
def test_knowledge_dir_has_no_extension(runtime: str):
    """Knowledge directory should not have a file extension."""
    lt_dir = RUNTIME_FILE_MAP[runtime][2]
    assert "." not in lt_dir, f"{runtime}: knowledge dir '{lt_dir}' looks like a file, not a directory"


# ------------------------------------------------------------------
# Specific runtime values
# ------------------------------------------------------------------

def test_claude_code_mapping():
    """Claude Code uses CLAUDE.md, memory.md, codex, handover.md."""
    char, mem, knowledge, handover = RUNTIME_FILE_MAP["claude-code"]
    assert char == "CLAUDE.md"
    assert mem == "memory.md"
    assert knowledge == "codex"
    assert handover == "handover.md"


def test_openai_codex_mapping():
    """OpenAI Codex uses AGENTS.md, memory.md, codex, handover.md."""
    char, mem, knowledge, handover = RUNTIME_FILE_MAP["openai-codex"]
    assert char == "AGENTS.md"
    assert mem == "memory.md"
    assert knowledge == "codex"
    assert handover == "handover.md"


def test_lingtai_mapping():
    """LingTai uses lingtai.md, pad.md, codex, system/summaries."""
    char, mem, knowledge, handover = RUNTIME_FILE_MAP["lingtai"]
    assert char == "lingtai.md"
    assert mem == "pad.md"
    assert knowledge == "codex"
    assert handover == "system/summaries"


def test_hermes_mapping():
    """Hermes uses identity.md, goals.md, memory, handover.md."""
    char, mem, knowledge, handover = RUNTIME_FILE_MAP["hermes"]
    assert char == "identity.md"
    assert mem == "goals.md"
    assert knowledge == "memory"
    assert handover == "handover.md"

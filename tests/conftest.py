"""Shared fixtures for lingtai-node tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lingtai_node.contracts import RUNTIME_FILE_MAP


@pytest.fixture
def tmp_node_dir(tmp_path: Path) -> Path:
    """Create a minimal valid node directory for claude-code runtime."""
    return _make_node_dir(tmp_path / "test-node", runtime="claude-code")


@pytest.fixture
def tmp_node_dir_factory(tmp_path: Path):
    """Factory fixture: create a valid node directory for any runtime."""
    def _factory(name: str = "test-node", runtime: str = "claude-code") -> Path:
        return _make_node_dir(tmp_path / name, runtime=runtime)
    return _factory


@pytest.fixture
def tmp_empty_dir(tmp_path: Path) -> Path:
    """Create an empty directory (no node structure)."""
    d = tmp_path / "empty-node"
    d.mkdir()
    return d


def _make_node_dir(node_dir: Path, runtime: str = "claude-code") -> Path:
    """Build a fully valid node directory for the given runtime."""
    node_dir.mkdir(parents=True, exist_ok=True)

    # .agent.json
    agent_meta = {
        "name": node_dir.name,
        "runtime": runtime,
        "contract_version": "2.0.0",
    }
    (node_dir / ".agent.json").write_text(
        json.dumps(agent_meta, indent=2), encoding="utf-8",
    )

    # Runtime-specific files
    char_file, mem_file, lt_dir, handover_path = RUNTIME_FILE_MAP[runtime]
    (node_dir / char_file).write_text(f"# Identity for {runtime}", encoding="utf-8")
    (node_dir / mem_file).write_text(f"# Memory for {runtime}", encoding="utf-8")

    # Handover: may be a file (handover.md) or a directory (system/summaries)
    hp = node_dir / handover_path
    if handover_path.endswith(".md"):
        hp.write_text("# Handover", encoding="utf-8")
    else:
        hp.mkdir(parents=True, exist_ok=True)

    # Mailbox
    (node_dir / "mailbox" / "inbox").mkdir(parents=True)
    (node_dir / "mailbox" / "sent").mkdir(parents=True)
    (node_dir / "mailbox" / "archive").mkdir(parents=True)

    # Knowledge store
    lt_path = node_dir / lt_dir
    lt_path.mkdir(parents=True, exist_ok=True)

    return node_dir

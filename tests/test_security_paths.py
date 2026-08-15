"""Regression tests for path confinement of MCP-exposed managers."""
from __future__ import annotations

from pathlib import Path

import pytest

from lingtai_node.avatar_manager import AvatarManager
from lingtai_node.email_manager import EmailManager
from lingtai_node.security import safe_child
from lingtai_node.system_manager import SystemManager


def test_safe_child_rejects_parent_traversal(tmp_path: Path):
    with pytest.raises(ValueError):
        safe_child(tmp_path, "../outside")


def test_safe_child_rejects_absolute_path(tmp_path: Path):
    with pytest.raises(ValueError):
        safe_child(tmp_path, "/tmp/outside")


def test_email_local_delivery_rejects_traversal(tmp_path: Path):
    agent_dir = tmp_path / "sender"
    agent_dir.mkdir()
    manager = EmailManager(agent_dir, agent_name="sender")

    result = manager.handle({
        "action": "send",
        "to": "../outside",
        "subject": "hello",
        "body": "body",
    })

    assert "error" in result
    assert not (tmp_path.parent / "outside" / "mailbox" / "inbox").exists()


def test_system_target_rejects_traversal(tmp_path: Path):
    agent_dir = tmp_path / "node"
    agent_dir.mkdir()
    manager = SystemManager(agent_dir)

    result = manager.handle({
        "action": "wake",
        "target": "../outside",
        "prompt": "wake up",
    })

    assert "error" in result
    assert not (tmp_path.parent / "outside" / ".prompt").exists()


def test_avatar_spawn_rejects_traversal(tmp_path: Path):
    agent_dir = tmp_path / "node"
    agent_dir.mkdir()
    manager = AvatarManager(agent_dir)

    result = manager.handle({
        "action": "spawn",
        "name": "../outside",
        "mission": "mission",
    })

    assert "error" in result
    assert not (tmp_path.parent / "outside").exists()

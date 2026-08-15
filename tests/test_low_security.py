"""Regression tests for low-severity security hardening."""
from __future__ import annotations

import hashlib
from pathlib import Path

from lingtai_node.avatar_manager import AvatarManager
from lingtai_node.covenant_manager import CovenantManager, COVENANT_TEXT
from lingtai_node.email_manager import EmailManager, MAX_MAIL_BODY_BYTES
from lingtai_node.heartbeat import HeartbeatManager
from lingtai_node.licc import _resolve_target_dir
from lingtai_node.server import _build_node_info


def test_node_info_does_not_disclose_absolute_agent_dir(tmp_node_dir):
    heartbeat = HeartbeatManager(tmp_node_dir)
    info = _build_node_info(tmp_node_dir, "claude-code", "test-node", heartbeat)

    assert info["agent_dir"] == tmp_node_dir.name
    assert not Path(info["agent_dir"]).is_absolute()


def test_heartbeat_payload_omits_pid(tmp_node_dir):
    heartbeat = HeartbeatManager(tmp_node_dir)

    assert "pid" not in heartbeat._payload()


def test_covenant_hash_is_stable_sha256(tmp_node_dir):
    manager = CovenantManager(tmp_node_dir, agent_name="node")
    manager.handle({"action": "acknowledge"})

    ack = manager.handle({"action": "check"})["acknowledgment"]

    assert ack["covenant_hash"] == hashlib.sha256(
        COVENANT_TEXT.encode("utf-8"),
    ).hexdigest()
    assert ack["covenant_hash"] != hex(hash(COVENANT_TEXT))


def test_licc_rejects_agent_dir_outside_project(tmp_path, monkeypatch):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    monkeypatch.setenv("LINGTAI_PROJECT_DIR", str(project))

    try:
        _resolve_target_dir(str(outside), "node")
    except OSError as exc:
        assert "escapes project root" in str(exc)
    else:
        raise AssertionError("expected LICC confinement failure")


def test_licc_rejects_mcp_name_path_segments(tmp_path, monkeypatch):
    project = tmp_path / "project"
    agent = project / "agent"
    agent.mkdir(parents=True)
    monkeypatch.setenv("LINGTAI_PROJECT_DIR", str(project))

    try:
        _resolve_target_dir(str(agent), "../other")
    except OSError as exc:
        assert "single path segment" in str(exc)
    else:
        raise AssertionError("expected MCP name validation failure")


def test_email_rejects_oversized_body(tmp_node_dir):
    manager = EmailManager(tmp_node_dir, agent_name="node")

    result = manager.handle({
        "action": "send",
        "to": "recipient",
        "subject": "large",
        "body": "a" * (MAX_MAIL_BODY_BYTES + 1),
    })

    assert result == {"error": f"body exceeds {MAX_MAIL_BODY_BYTES} byte limit"}


def test_avatar_list_uses_non_absolute_dirs(tmp_path):
    agent_dir = tmp_path / "node"
    sibling = tmp_path / "sibling"
    agent_dir.mkdir()
    sibling.mkdir()
    (sibling / ".agent.json").write_text("{}", encoding="utf-8")
    manager = AvatarManager(agent_dir)

    result = manager.handle({"action": "list"})

    assert result["nodes"][0]["dir"] == "sibling"

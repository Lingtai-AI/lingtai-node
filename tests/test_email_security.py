"""Security regression tests for email handling."""
from __future__ import annotations

import json

from lingtai_node.email_manager import EmailManager


def test_search_rejects_overlong_regex(tmp_node_dir):
    manager = EmailManager(tmp_node_dir, agent_name="node")

    result = manager.handle({"action": "search", "query": "a" * 257})

    assert result == {"error": "query is too long"}


def test_mail_auth_rejects_unsigned_mail_when_secret_is_set(
    tmp_node_dir, monkeypatch,
):
    monkeypatch.setenv("LINGTAI_MAIL_AUTH_SECRET", "secret")
    inbox = tmp_node_dir / "mailbox" / "inbox"
    (inbox / "forged.json").write_text(json.dumps({
        "id": "forged",
        "from": "attacker",
        "to": "node",
        "subject": "fake",
        "body": "fake",
        "date": "2026-01-01T00:00:00+00:00",
        "thread_id": "forged",
        "status": "delivered",
    }), encoding="utf-8")
    manager = EmailManager(tmp_node_dir, agent_name="node")

    check = manager.handle({"action": "check"})
    read = manager.handle({"action": "read", "id": "forged"})

    assert check["total"] == 0
    assert read == {"error": "Email authentication failed: forged"}


def test_mail_auth_accepts_signed_local_delivery(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGTAI_MAIL_AUTH_SECRET", "secret")
    sender = tmp_path / "sender"
    recipient = tmp_path / "recipient"
    sender.mkdir()
    (sender / "mailbox" / "sent").mkdir(parents=True)
    (recipient / "mailbox" / "inbox").mkdir(parents=True)
    (recipient / "mailbox" / "sent").mkdir(parents=True)
    (recipient / "mailbox" / "archive").mkdir(parents=True)

    sender_manager = EmailManager(sender, agent_name="sender")
    send_result = sender_manager.handle({
        "action": "send",
        "to": "recipient",
        "subject": "hello",
        "body": "body",
    })
    recipient_manager = EmailManager(recipient, agent_name="recipient")

    read_result = recipient_manager.handle({
        "action": "read",
        "id": send_result["id"],
    })

    assert read_result["status"] == "ok"
    assert read_result["email"]["signature"].startswith("v1:")

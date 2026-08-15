"""Security regression tests for runtime session logging."""
from __future__ import annotations

import logging

from lingtai_node.runtimes.claude_code.session import ClaudeCodeSessionManager


def test_claude_session_does_not_log_prompt(tmp_node_dir, caplog, monkeypatch):
    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    manager = ClaudeCodeSessionManager(tmp_node_dir)

    with caplog.at_level(logging.INFO):
        manager.start("secret prompt")

    assert "secret prompt" not in caplog.text
    assert "<redacted prompt>" in caplog.text

"""Claude Code session manager.

Every interaction resumes the same persistent session via ``--continue``.
Claude Code stores sessions in its own session store; the ``--continue``
flag resumes the most recent session in the current working directory.
Prompts are executed via the ``claude`` CLI in non-interactive mode.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from ..base import SessionManager

log = logging.getLogger(__name__)


class ClaudeCodeSessionManager(SessionManager):
    """Drive Claude Code via ``claude --continue``."""

    def __init__(
        self,
        agent_dir: Path,
        *,
        model: str = "opus",
        effort: str = "max",
    ) -> None:
        super().__init__(agent_dir)
        self._model = model
        self._effort = effort
        self._initialized = False  # first call creates session, subsequent resume

    def session_id(self) -> str | None:
        """Return None — Claude Code manages session IDs internally."""
        return None

    def start(self, prompt: str) -> dict[str, Any]:
        """Send *prompt* to Claude Code and return captured output.

        First call: ``claude -p <prompt>`` (creates new session).
        Subsequent calls: ``claude -p <prompt> --continue`` (resumes).
        """
        cmd = [
            "claude",
            "-p", prompt,
            "--dangerously-skip-permissions",
            "--model", self._model,
            "--effort", self._effort,
        ]

        # After the first call, use --continue to resume the session
        if self._initialized:
            cmd.append("--continue")

        log.info("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self._agent_dir),
                timeout=600,  # 10 minute timeout
            )
        except FileNotFoundError:
            log.error("'claude' CLI not found on PATH")
            return {
                "stdout": "",
                "stderr": "'claude' CLI not found on PATH",
                "returncode": 127,
            }
        except subprocess.TimeoutExpired:
            log.error("Claude Code timed out after 600s")
            return {
                "stdout": "",
                "stderr": "Claude Code timed out after 600s",
                "returncode": 124,
            }
        except Exception as exc:
            log.error("Subprocess failed: %s", exc)
            return {
                "stdout": "",
                "stderr": str(exc),
                "returncode": 1,
            }

        # Mark as initialized after first successful call
        if result.returncode == 0:
            self._initialized = True

        log.info(
            "claude exited %d (stdout=%d bytes, stderr=%d bytes)",
            result.returncode,
            len(result.stdout),
            len(result.stderr),
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

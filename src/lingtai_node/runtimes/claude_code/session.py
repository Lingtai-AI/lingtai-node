"""Claude Code session manager.

Every interaction resumes the same persistent session.  The session ID is
stored in ``{agent_dir}/.session_id`` so it survives process restarts.
Prompts are executed via the ``claude`` CLI in non-interactive mode.
"""
from __future__ import annotations

import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Any

from ..base import SessionManager

log = logging.getLogger(__name__)

SESSION_ID_FILENAME = ".session_id"


class ClaudeCodeSessionManager(SessionManager):
    """Drive Claude Code via ``claude --resume``."""

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
        self._session_id_path = self._agent_dir / SESSION_ID_FILENAME
        self._sid: str | None = None
        self._load_session_id()

    # ------------------------------------------------------------------
    # Session ID persistence
    # ------------------------------------------------------------------

    def _load_session_id(self) -> None:
        """Load an existing session ID from disk, or create a new one."""
        if self._session_id_path.is_file():
            try:
                sid = self._session_id_path.read_text(encoding="utf-8").strip()
                if sid:
                    self._sid = sid
                    log.info("Loaded session %s", self._sid)
                    return
            except OSError as exc:
                log.warning("Failed to read session ID file: %s", exc)

        self._sid = str(uuid.uuid4())
        self._save_session_id()
        log.info("Created new session %s", self._sid)

    def _save_session_id(self) -> None:
        self._agent_dir.mkdir(parents=True, exist_ok=True)
        self._session_id_path.write_text(self._sid + "\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def session_id(self) -> str | None:  # noqa: D401
        return self._sid

    def start(self, prompt: str) -> dict[str, Any]:
        """Send *prompt* to Claude Code and return captured output."""
        cmd = [
            "claude",
            "--session-id", self._sid,
            "--resume",
            "-p", prompt,
            "--dangerously-skip-permissions",
            "--model", self._model,
            "--effort", self._effort,
        ]

        log.info("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self._agent_dir),
            )
        except FileNotFoundError:
            log.error("'claude' CLI not found on PATH")
            return {
                "stdout": "",
                "stderr": "'claude' CLI not found on PATH",
                "returncode": 127,
            }
        except Exception as exc:
            log.error("Subprocess failed: %s", exc)
            return {
                "stdout": "",
                "stderr": str(exc),
                "returncode": 1,
            }

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

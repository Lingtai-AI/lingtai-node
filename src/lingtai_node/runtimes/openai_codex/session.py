"""OpenAI Codex session manager.

Every interaction resumes the same persistent session via ``codex exec resume --last``.
Codex CLI stores sessions in ~/.codex/sessions/; the ``resume --last`` flag resumes
the most recent session in the current working directory.

Prompts are executed via the ``codex`` CLI in non-interactive mode.

The AGENTS.md file in the agent directory is automatically loaded by
Codex as its system prompt. This file contains the pre-compact ritual
(what to save before context is shed) and the post-compact recovery
instructions (what to read after compaction).
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from ..base import SessionManager

log = logging.getLogger(__name__)


class OpenAICodexSessionManager(SessionManager):
    """Drive OpenAI Codex via ``codex exec resume --last``."""

    def __init__(
        self,
        agent_dir: Path,
        *,
        model: str = "o3",
    ) -> None:
        super().__init__(agent_dir)
        self._model = model
        self._initialized = False  # first call creates session, subsequent resume

    def session_id(self) -> str | None:
        """Return None — Codex manages session IDs internally."""
        return None

    def start(self, prompt: str) -> dict[str, Any]:
        """Send *prompt* to Codex CLI and return captured output.

        First call: ``codex exec "prompt"`` (creates new session).
        Subsequent calls: ``codex exec resume --last "prompt"`` (resumes).

        Codex automatically loads AGENTS.md from the working directory
        as its system prompt. This file contains the pre-compact ritual and
        character definition, so we don't need to pass it explicitly.
        """
        if self._initialized:
            # Resume the most recent session
            cmd = [
                "codex",
                "exec",
                "resume",
                "--last",
                prompt,
            ]
        else:
            # Create a new session
            cmd = [
                "codex",
                "exec",
                prompt,
            ]

        # Add model flag if specified
        if self._model:
            cmd.extend(["--model", self._model])

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
            log.error("'codex' CLI not found on PATH")
            return {
                "stdout": "",
                "stderr": "'codex' CLI not found on PATH",
                "exit_code": 127,
            }
        except subprocess.TimeoutExpired:
            log.error("Codex timed out after 600s")
            return {
                "stdout": "",
                "stderr": "Codex timed out after 600 seconds",
                "exit_code": 124,
            }

        # Mark as initialized after first successful call
        if result.returncode == 0:
            self._initialized = True

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }

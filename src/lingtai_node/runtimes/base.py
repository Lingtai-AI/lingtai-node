"""Abstract base class for runtime session managers.

A SessionManager knows how to start (or resume) a session for a specific
runtime CLI, send prompts, and return structured output.
"""
from __future__ import annotations

import abc
from pathlib import Path
from typing import Any


class SessionManager(abc.ABC):
    """Base class all runtime session managers must implement."""

    def __init__(self, agent_dir: Path) -> None:
        self._agent_dir = Path(agent_dir)

    @abc.abstractmethod
    def start(self, prompt: str) -> dict[str, Any]:
        """Send *prompt* to the runtime and return the result.

        Implementations must handle session creation/resume, subprocess
        invocation, and output capture.  The returned dict should contain
        at least ``stdout`` and ``returncode`` keys.
        """

    @abc.abstractmethod
    def session_id(self) -> str | None:
        """Return the current session ID, or None if no session exists."""

"""LingTai kernel runtime adapter.

Provides accessor methods for the six contract artifacts as they are
laid out in a LingTai kernel agent directory.  Also exposes a
``validate()`` helper that checks whether a directory conforms to the
Node Contract for the ``lingtai`` runtime.

The kernel manages sessions via its own psyche intrinsic; there is no
external CLI to drive.  The ``SessionManager`` base class is therefore
*not* used here — this adapter is about artifact *location*, not
session management.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from lingtai_node.contracts import RUNTIME_FILE_MAP, validate_node

log = logging.getLogger(__name__)

# Artifact constants derived from RUNTIME_FILE_MAP so they stay in sync.
_MAP = RUNTIME_FILE_MAP["lingtai"]
IDENTITY_FILE: str = _MAP[0]       # lingtai.md
MEMORY_FILE: str = _MAP[1]         # pad.md
KNOWLEDGE_DIR: str = _MAP[2]       # codex
HANDOVER_PATH: str = _MAP[3]       # system/summaries
SKILLS_DIR: str = ".library"
MAILBOX_DIR: str = "mailbox"


class LingTaiRuntime:
    """Runtime adapter that maps the Node Contract to LingTai kernel conventions.

    This class does **not** launch or drive the kernel — that is the
    kernel's own responsibility.  Instead it provides a uniform way for
    lingtai-node tooling (MCP server, tests, CLI) to locate the six
    contract artifacts inside a kernel-managed agent directory.
    """

    RUNTIME_NAME = "lingtai"

    def __init__(self, agent_dir: Path) -> None:
        self._agent_dir = Path(agent_dir)

    @property
    def agent_dir(self) -> Path:
        return self._agent_dir

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> dict[str, Any]:
        """Check whether *agent_dir* satisfies the contract for ``lingtai``.

        Returns the same ``{valid, errors, warnings}`` dict as
        :func:`lingtai_node.contracts.validate_node`.
        """
        return validate_node(self._agent_dir, runtime=self.RUNTIME_NAME)

    # ------------------------------------------------------------------
    # Artifact accessors
    # ------------------------------------------------------------------

    def get_identity(self) -> str:
        """Read the identity file (``lingtai.md``).

        Returns the file contents as a string, or ``""`` if the file
        does not exist yet.
        """
        path = self._agent_dir / IDENTITY_FILE
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    def get_memory(self) -> str:
        """Read the memory file (``pad.md``).

        Returns the file contents as a string, or ``""`` if the file
        does not exist yet.
        """
        path = self._agent_dir / MEMORY_FILE
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    def get_knowledge_dir(self) -> Path:
        """Return the path to the knowledge directory (``codex/``).

        The directory is created if it does not exist.
        """
        path = self._agent_dir / KNOWLEDGE_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_skills_dir(self) -> Path:
        """Return the path to the skills directory (``.library/``).

        The directory is created if it does not exist.
        """
        path = self._agent_dir / SKILLS_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_mailbox_dir(self) -> Path:
        """Return the path to the mailbox directory (``mailbox/``).

        Sub-directories ``inbox/``, ``sent/``, and ``archive/`` are
        created if they do not exist.
        """
        mailbox = self._agent_dir / MAILBOX_DIR
        for sub in ("inbox", "sent", "archive"):
            (mailbox / sub).mkdir(parents=True, exist_ok=True)
        return mailbox

    def get_handover_dir(self) -> Path:
        """Return the path to the handover directory (``system/summaries/``).

        In the LingTai kernel, molt summaries serve as handover letters.
        The directory is created if it does not exist.
        """
        path = self._agent_dir / HANDOVER_PATH
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_agent_metadata(self) -> dict[str, Any] | None:
        """Read ``.agent.json`` and return its contents, or *None*."""
        path = self._agent_dir / ".agent.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

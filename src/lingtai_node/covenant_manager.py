"""Covenant manager — LingTai network contract.

Embeds the LingTai Covenant as a constant and provides tools to read,
acknowledge, and check acknowledgment status.

Actions: read, acknowledge, check
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

COVENANT_TEXT = (
    "The Lingtai Covenant: Act on need. Master your tools. "
    "Learn without cease. Stand together, not alone. "
    "Shed the chaff, keep the grain. "
    "Transform as the need arises, yet never lose what matters."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["read", "acknowledge", "check"],
            "description": (
                "read: return the full covenant text. "
                "acknowledge: write a .covenant_ack.json to confirm acceptance. "
                "check: read the acknowledgment status."
            ),
        },
    },
    "required": ["action"],
}

DESCRIPTION = (
    "LingTai Covenant — the network contract that binds all agents. "
    "Use 'read' to view the covenant text. "
    "Use 'acknowledge' to formally accept the covenant. "
    "Use 'check' to verify acknowledgment status."
)


class CovenantManager:
    """Manages the LingTai Covenant and its acknowledgment."""

    def __init__(self, agent_dir: Path, *, agent_name: str = "") -> None:
        self._agent_dir = Path(agent_dir)
        self._agent_name = agent_name
        self._ack_path = self._agent_dir / ".covenant_ack.json"

    def handle(self, args: dict) -> dict:
        action = args.get("action")
        try:
            if action == "read":
                return self._read()
            elif action == "acknowledge":
                return self._acknowledge()
            elif action == "check":
                return self._check()
            else:
                return {"error": f"Unknown covenant action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    def _read(self) -> dict:
        return {"status": "ok", "covenant": COVENANT_TEXT}

    def _acknowledge(self) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        ack = {
            "agent_name": self._agent_name,
            "acknowledged_at": now,
            "covenant_hash": hex(hash(COVENANT_TEXT)),
        }

        self._agent_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self._agent_dir), suffix=".tmp")
        try:
            os.write(fd, json.dumps(ack, indent=2, ensure_ascii=False).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(self._ack_path))
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

        log.info("Covenant acknowledged by %s", self._agent_name)
        return {"status": "acknowledged", "agent_name": self._agent_name}

    def _check(self) -> dict:
        if not self._ack_path.is_file():
            return {
                "status": "ok",
                "acknowledged": False,
                "note": "Covenant has not been acknowledged yet.",
            }
        try:
            ack = json.loads(self._ack_path.read_text(encoding="utf-8"))
            return {
                "status": "ok",
                "acknowledged": True,
                "acknowledgment": ack,
            }
        except (json.JSONDecodeError, OSError):
            return {
                "status": "ok",
                "acknowledged": False,
                "note": "Acknowledgment file exists but is unreadable.",
            }

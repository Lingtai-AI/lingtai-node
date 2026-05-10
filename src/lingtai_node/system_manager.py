"""System manager — write signal files to control other LingTai nodes.

Provides inter-node control by writing signal files (.prompt, .sleep,
.suspend) to target node directories and reading their status.

Actions: wake, sleep, suspend, status, list_nodes
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

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["wake", "sleep", "suspend", "status", "list_nodes"],
            "description": (
                "wake: write a .prompt file with prompt text to a target node. "
                "sleep: write a .sleep signal file to a target node. "
                "suspend: write a .suspend signal file to a target node. "
                "status: read the .heartbeat from a target node. "
                "list_nodes: scan parent directory for directories with .agent.json."
            ),
        },
        "target": {
            "type": "string",
            "description": "Target node name (for wake, sleep, suspend, status)",
        },
        "prompt": {
            "type": "string",
            "description": "Prompt text to write to .prompt file (for wake)",
        },
    },
    "required": ["action"],
}

DESCRIPTION = (
    "System manager — control other LingTai nodes via signal files. "
    "Use 'wake' to write a .prompt file to a target node (target, prompt). "
    "Use 'sleep' to write a .sleep signal to a target node. "
    "Use 'suspend' to write a .suspend signal to a target node. "
    "Use 'status' to read a target node's heartbeat. "
    "Use 'list_nodes' to discover all nodes in the parent directory."
)


class SystemManager:
    """Writes signal files to control sibling LingTai nodes."""

    def __init__(self, agent_dir: Path, *, agent_name: str = "") -> None:
        self._agent_dir = Path(agent_dir)
        self._parent_dir = self._agent_dir.parent
        self._agent_name = agent_name

    def handle(self, args: dict) -> dict:
        action = args.get("action")
        try:
            if action == "wake":
                return self._wake(args)
            elif action == "sleep":
                return self._sleep(args)
            elif action == "suspend":
                return self._suspend(args)
            elif action == "status":
                return self._status(args)
            elif action == "list_nodes":
                return self._list_nodes()
            else:
                return {"error": f"Unknown system action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    def _resolve_target(self, args: dict) -> Path | None:
        """Resolve a target node name to its directory path."""
        target = args.get("target", "")
        if not target:
            return None
        return self._parent_dir / target

    def _write_signal(self, target_dir: Path, filename: str, data: dict) -> None:
        """Write a signal file atomically to a target directory."""
        target_path = target_dir / filename
        fd, tmp = tempfile.mkstemp(dir=str(target_dir), suffix=".tmp")
        try:
            os.write(fd, json.dumps(data, indent=2).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(target_path))
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def _wake(self, args: dict) -> dict:
        target_dir = self._resolve_target(args)
        if target_dir is None:
            return {"error": "target is required"}
        if not target_dir.is_dir():
            return {"error": f"Target node not found: {args.get('target')}"}

        prompt = args.get("prompt", "")
        if not prompt:
            return {"error": "prompt is required"}

        prompt_path = target_dir / ".prompt"
        prompt_path.write_text(prompt, encoding="utf-8")

        log.info("Wrote .prompt to %s", target_dir.name)
        return {"status": "prompted", "target": target_dir.name}

    def _sleep(self, args: dict) -> dict:
        target_dir = self._resolve_target(args)
        if target_dir is None:
            return {"error": "target is required"}
        if not target_dir.is_dir():
            return {"error": f"Target node not found: {args.get('target')}"}

        self._write_signal(target_dir, ".sleep", {})

        log.info("Wrote .sleep to %s", target_dir.name)
        return {"status": "sleeping", "target": target_dir.name}

    def _suspend(self, args: dict) -> dict:
        target_dir = self._resolve_target(args)
        if target_dir is None:
            return {"error": "target is required"}
        if not target_dir.is_dir():
            return {"error": f"Target node not found: {args.get('target')}"}

        self._write_signal(target_dir, ".suspend", {})

        log.info("Wrote .suspend to %s", target_dir.name)
        return {"status": "suspended", "target": target_dir.name}

    def _status(self, args: dict) -> dict:
        target_dir = self._resolve_target(args)
        if target_dir is None:
            return {"error": "target is required"}
        if not target_dir.is_dir():
            return {"error": f"Target node not found: {args.get('target')}"}

        heartbeat_path = target_dir / ".agent.heartbeat"
        if not heartbeat_path.is_file():
            return {
                "status": "ok",
                "target": target_dir.name,
                "heartbeat": None,
                "note": "No heartbeat file found",
            }
        try:
            hb = json.loads(heartbeat_path.read_text(encoding="utf-8"))
            return {
                "status": "ok",
                "target": target_dir.name,
                "heartbeat": hb,
            }
        except (json.JSONDecodeError, OSError):
            return {
                "status": "ok",
                "target": target_dir.name,
                "heartbeat": None,
                "note": "Heartbeat file unreadable",
            }

    def _list_nodes(self) -> dict:
        nodes: list[dict] = []
        if not self._parent_dir.is_dir():
            return {"status": "ok", "total": 0, "nodes": nodes}

        for entry in sorted(self._parent_dir.iterdir()):
            if not entry.is_dir():
                continue
            agent_json = entry / ".agent.json"
            if not agent_json.is_file():
                continue

            node: dict = {"name": entry.name, "dir": str(entry)}

            # Read agent metadata
            try:
                meta = json.loads(agent_json.read_text(encoding="utf-8"))
                node["runtime"] = meta.get("runtime", "unknown")
            except (json.JSONDecodeError, OSError):
                node["runtime"] = "unknown"

            # Check signal state
            node["alive"] = (entry / ".agent.heartbeat").is_file()
            node["suspended"] = (entry / ".suspend").is_file()
            node["sleeping"] = (entry / ".sleep").is_file()
            node["has_prompt"] = (entry / ".prompt").is_file()

            nodes.append(node)

        return {"status": "ok", "total": len(nodes), "nodes": nodes}

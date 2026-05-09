"""Avatar manager — spawn, list, and terminate LingTai nodes.

Manages the lifecycle of sibling agent nodes within the same parent
directory. Spawning creates the directory structure and metadata files
but does NOT launch a runtime — the node is ready to be picked up by
whatever runtime the operator chooses.

Actions: spawn, list, terminate
"""
from __future__ import annotations

import json
import logging
import os
import shutil
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
            "enum": ["spawn", "list", "terminate"],
            "description": (
                "spawn: create a new node directory with mailbox, codex, "
                "agent metadata, covenant, and mission prompt. "
                "list: scan parent directory for sibling nodes and their status. "
                "terminate: write a .suspend file to a target node directory."
            ),
        },
        "name": {
            "type": "string",
            "description": "Node name (for spawn, terminate)",
        },
        "mission": {
            "type": "string",
            "description": "Mission briefing text written to .prompt file (for spawn)",
        },
        "runtime": {
            "type": "string",
            "description": "Runtime type for the new node (default: claude-code)",
        },
    },
    "required": ["action"],
}

DESCRIPTION = (
    "Avatar manager — spawn, list, and terminate LingTai agent nodes. "
    "Use 'spawn' to create a new node directory (name, mission; optional runtime). "
    "Use 'list' to scan for sibling nodes and their heartbeat status. "
    "Use 'terminate' to write a .suspend signal file to a target node."
)


class AvatarManager:
    """Manages spawning and lifecycle of sibling agent nodes."""

    def __init__(self, agent_dir: Path) -> None:
        self._agent_dir = Path(agent_dir)
        self._parent_dir = self._agent_dir.parent

    def handle(self, args: dict) -> dict:
        action = args.get("action")
        try:
            if action == "spawn":
                return self._spawn(args)
            elif action == "list":
                return self._list()
            elif action == "terminate":
                return self._terminate(args)
            else:
                return {"error": f"Unknown avatar action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    def _spawn(self, args: dict) -> dict:
        name = args.get("name", "")
        if not name:
            return {"error": "name is required"}

        mission = args.get("mission", "")
        if not mission:
            return {"error": "mission is required"}

        runtime = args.get("runtime", "claude-code")

        node_dir = self._parent_dir / name
        if node_dir.exists():
            return {"error": f"Node directory already exists: {node_dir}"}

        # Create directory structure
        node_dir.mkdir(parents=True, exist_ok=True)
        (node_dir / "mailbox" / "inbox").mkdir(parents=True, exist_ok=True)
        (node_dir / "mailbox" / "sent").mkdir(parents=True, exist_ok=True)
        (node_dir / "mailbox" / "archive").mkdir(parents=True, exist_ok=True)

        # Create codex
        codex_dir = node_dir / "codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        (codex_dir / "codex.json").write_text("[]", encoding="utf-8")

        # Create .agent.json
        now = datetime.now(timezone.utc).isoformat()
        agent_meta = {
            "name": name,
            "runtime": runtime,
            "spawned_by": self._agent_dir.name,
            "spawned_at": now,
        }
        (node_dir / ".agent.json").write_text(
            json.dumps(agent_meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Copy covenant.md from our own directory if it exists
        our_covenant = self._agent_dir / "covenant.md"
        if our_covenant.is_file():
            shutil.copy2(str(our_covenant), str(node_dir / "covenant.md"))

        # Write mission briefing to .prompt
        (node_dir / ".prompt").write_text(mission, encoding="utf-8")

        log.info("Spawned node: %s at %s", name, node_dir)
        return {
            "status": "spawned",
            "name": name,
            "node_dir": str(node_dir),
            "runtime": runtime,
        }

    def _list(self) -> dict:
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
                node["spawned_by"] = meta.get("spawned_by")
                node["spawned_at"] = meta.get("spawned_at")
            except (json.JSONDecodeError, OSError):
                node["runtime"] = "unknown"

            # Read heartbeat
            heartbeat_path = entry / ".heartbeat"
            if heartbeat_path.is_file():
                try:
                    hb = json.loads(heartbeat_path.read_text(encoding="utf-8"))
                    node["heartbeat"] = hb
                except (json.JSONDecodeError, OSError):
                    node["heartbeat"] = None
            else:
                node["heartbeat"] = None

            # Check signal files
            node["suspended"] = (entry / ".suspend").is_file()
            node["sleeping"] = (entry / ".sleep").is_file()
            node["has_prompt"] = (entry / ".prompt").is_file()

            nodes.append(node)

        return {"status": "ok", "total": len(nodes), "nodes": nodes}

    def _terminate(self, args: dict) -> dict:
        name = args.get("name", "")
        if not name:
            return {"error": "name is required"}

        target_dir = self._parent_dir / name
        if not target_dir.is_dir():
            return {"error": f"Node directory not found: {name}"}

        suspend_path = target_dir / ".suspend"
        now = datetime.now(timezone.utc).isoformat()
        suspend_data = {
            "suspended_by": self._agent_dir.name,
            "suspended_at": now,
        }

        fd, tmp = tempfile.mkstemp(dir=str(target_dir), suffix=".tmp")
        try:
            os.write(fd, json.dumps(suspend_data, indent=2).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(suspend_path))
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

        log.info("Terminated node: %s", name)
        return {"status": "terminated", "name": name}

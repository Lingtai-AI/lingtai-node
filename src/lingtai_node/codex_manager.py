"""Codex manager — knowledge store operations.

Manages the codex/codex.json file in the agent directory. Each entry
has an id, title, content, tags, and timestamps.

Actions: view, submit, consolidate, delete
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

log = logging.getLogger(__name__)

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["view", "submit", "consolidate", "delete"],
            "description": (
                "view: list all codex entries (optional tag filter). "
                "submit: add a new entry (title, content; optional tags). "
                "consolidate: merge entries by tag into a single entry. "
                "delete: remove an entry by id."
            ),
        },
        "id": {
            "type": "string",
            "description": "Entry ID (for delete)",
        },
        "title": {
            "type": "string",
            "description": "Entry title (for submit)",
        },
        "content": {
            "type": "string",
            "description": "Entry content (for submit)",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tags (for submit, or filter for view)",
        },
        "tag": {
            "type": "string",
            "description": "Tag to consolidate entries by (for consolidate)",
        },
    },
    "required": ["action"],
}

DESCRIPTION = (
    "Knowledge store — persist and retrieve structured knowledge entries. "
    "Use 'view' to list entries (optionally filtered by tags). "
    "Use 'submit' to add new knowledge (title + content + optional tags). "
    "Use 'consolidate' to merge all entries with a given tag into one. "
    "Use 'delete' to remove an entry by id."
)


class CodexManager:
    """Manages the codex/codex.json knowledge store."""

    def __init__(self, agent_dir: Path) -> None:
        self._agent_dir = Path(agent_dir)
        self._codex_dir = self._agent_dir / "codex"
        self._codex_file = self._codex_dir / "codex.json"

    def _load(self) -> list[dict]:
        if not self._codex_file.is_file():
            return []
        try:
            data = json.loads(self._codex_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            # Support {"entries": [...]} wrapper
            if isinstance(data, dict) and "entries" in data:
                return data["entries"]
            return []
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, entries: list[dict]) -> None:
        self._codex_dir.mkdir(parents=True, exist_ok=True)
        target = self._codex_file
        fd, tmp = tempfile.mkstemp(
            dir=str(self._codex_dir), suffix=".tmp",
        )
        try:
            os.write(fd, json.dumps(entries, indent=2, ensure_ascii=False).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(target))
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def handle(self, args: dict) -> dict:
        action = args.get("action")
        try:
            if action == "view":
                return self._view(args)
            elif action == "submit":
                return self._submit(args)
            elif action == "consolidate":
                return self._consolidate(args)
            elif action == "delete":
                return self._delete(args)
            else:
                return {"error": f"Unknown codex action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    def _view(self, args: dict) -> dict:
        entries = self._load()
        tags = args.get("tags")
        if tags:
            tag_set = set(tags)
            entries = [
                e for e in entries
                if tag_set.intersection(e.get("tags", []))
            ]
        return {"status": "ok", "total": len(entries), "entries": entries}

    def _submit(self, args: dict) -> dict:
        title = args.get("title", "")
        content = args.get("content", "")
        if not title:
            return {"error": "title is required"}
        if not content:
            return {"error": "content is required"}

        entries = self._load()
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "id": uuid4().hex[:12],
            "title": title,
            "content": content,
            "tags": args.get("tags", []),
            "created_at": now,
            "updated_at": now,
        }
        entries.append(entry)
        self._save(entries)
        return {"status": "submitted", "id": entry["id"]}

    def _consolidate(self, args: dict) -> dict:
        tag = args.get("tag", "")
        if not tag:
            return {"error": "tag is required"}

        entries = self._load()
        matching = [e for e in entries if tag in e.get("tags", [])]
        if len(matching) < 2:
            return {"status": "noop", "reason": f"Need at least 2 entries with tag '{tag}' to consolidate, found {len(matching)}"}

        remaining = [e for e in entries if tag not in e.get("tags", [])]
        now = datetime.now(timezone.utc).isoformat()
        merged_content = "\n\n---\n\n".join(
            f"## {e.get('title', 'Untitled')}\n\n{e.get('content', '')}"
            for e in matching
        )
        consolidated = {
            "id": uuid4().hex[:12],
            "title": f"Consolidated: {tag}",
            "content": merged_content,
            "tags": list({t for e in matching for t in e.get("tags", [])}),
            "created_at": now,
            "updated_at": now,
            "consolidated_from": [e.get("id") for e in matching],
        }
        remaining.append(consolidated)
        self._save(remaining)
        return {
            "status": "consolidated",
            "id": consolidated["id"],
            "merged_count": len(matching),
        }

    def _delete(self, args: dict) -> dict:
        entry_id = args.get("id", "")
        if not entry_id:
            return {"error": "id is required"}

        entries = self._load()
        before = len(entries)
        entries = [e for e in entries if e.get("id") != entry_id]
        if len(entries) == before:
            return {"error": f"Entry not found: {entry_id}"}
        self._save(entries)
        return {"status": "deleted", "id": entry_id}

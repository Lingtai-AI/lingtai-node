"""Mapping manager — maps runtime-specific files to LingTai conventions.

Each runtime has its own names for character and memory files:
    lingtai:     character → lingtai.md,  memory → pad.md
    claude-code: character → CLAUDE.md,   memory → memory.md

Actions: get_character, set_character, get_memory, set_memory
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Runtime → (character_file, memory_file)
RUNTIME_MAPPINGS: dict[str, tuple[str, str]] = {
    "lingtai": ("lingtai.md", "pad.md"),
    "claude-code": ("CLAUDE.md", "memory.md"),
}

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["get_character", "set_character", "get_memory", "set_memory"],
            "description": (
                "get_character: read the character/persona file. "
                "set_character: write the character/persona file. "
                "get_memory: read the memory/scratchpad file. "
                "set_memory: write the memory/scratchpad file."
            ),
        },
        "content": {
            "type": "string",
            "description": "File content (for set_character, set_memory)",
        },
    },
    "required": ["action"],
}

DESCRIPTION = (
    "Character and memory file mapping — read and write runtime-specific "
    "persona and memory files. Maps to the correct filename based on the "
    "configured runtime (e.g., CLAUDE.md for claude-code, lingtai.md for lingtai)."
)


class MappingManager:
    """Maps character/memory operations to runtime-specific files."""

    def __init__(self, agent_dir: Path, runtime: str = "claude-code") -> None:
        self._agent_dir = Path(agent_dir)
        self._runtime = runtime
        mapping = RUNTIME_MAPPINGS.get(runtime, RUNTIME_MAPPINGS["claude-code"])
        self._character_file = mapping[0]
        self._memory_file = mapping[1]

    def handle(self, args: dict) -> dict:
        action = args.get("action")
        try:
            if action == "get_character":
                return self._get_file(self._character_file, "character")
            elif action == "set_character":
                return self._set_file(self._character_file, "character", args)
            elif action == "get_memory":
                return self._get_file(self._memory_file, "memory")
            elif action == "set_memory":
                return self._set_file(self._memory_file, "memory", args)
            else:
                return {"error": f"Unknown mapping action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    def _get_file(self, filename: str, label: str) -> dict:
        path = self._agent_dir / filename
        if not path.is_file():
            return {
                "status": "ok",
                "content": "",
                "note": f"{label} file not found: {filename}",
            }
        try:
            content = path.read_text(encoding="utf-8")
            return {"status": "ok", "file": filename, "content": content}
        except OSError as e:
            return {"error": f"Failed to read {label} file: {e}"}

    def _set_file(self, filename: str, label: str, args: dict) -> dict:
        content = args.get("content")
        if content is None:
            return {"error": "content is required"}
        path = self._agent_dir / filename
        try:
            path.write_text(content, encoding="utf-8")
            return {"status": "written", "file": filename}
        except OSError as e:
            return {"error": f"Failed to write {label} file: {e}"}

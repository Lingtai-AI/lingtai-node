"""Library manager — skill catalog from .library/ directory.

Reads the agent's .library/ directory and returns information about
available skills. Each skill is a subdirectory or file in .library/.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["info"],
            "description": "info: return the skill catalog from .library/ directory.",
        },
    },
    "required": ["action"],
}

DESCRIPTION = (
    "Skill catalog — list available skills from the agent's .library/ directory. "
    "Use 'info' to get the full catalog."
)


class LibraryManager:
    """Reads the .library/ directory for the skill catalog."""

    def __init__(self, agent_dir: Path) -> None:
        self._agent_dir = Path(agent_dir)
        self._library_dir = self._agent_dir / ".library"

    def handle(self, args: dict) -> dict:
        action = args.get("action")
        try:
            if action == "info":
                return self._info()
            else:
                return {"error": f"Unknown library action: {action}"}
        except Exception as e:
            return {"error": str(e)}

    def _info(self) -> dict:
        if not self._library_dir.is_dir():
            return {"status": "ok", "skills": [], "note": ".library/ directory not found"}

        skills: list[dict] = []
        for entry in sorted(self._library_dir.iterdir()):
            if entry.name.startswith("."):
                continue

            skill: dict = {"name": entry.name}

            if entry.is_dir():
                # Look for metadata files
                meta_file = entry / "meta.json"
                readme = entry / "README.md"
                if meta_file.is_file():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        skill.update(meta)
                    except (json.JSONDecodeError, OSError):
                        pass
                if readme.is_file():
                    try:
                        skill["readme"] = readme.read_text(encoding="utf-8")
                    except OSError:
                        pass
                # List files in the skill directory
                files = [
                    f.name for f in entry.iterdir()
                    if not f.name.startswith(".")
                ]
                skill["files"] = sorted(files)
                skill["type"] = "directory"
            elif entry.is_file():
                skill["type"] = "file"
                skill["size"] = entry.stat().st_size
                # Read content for small files
                if entry.suffix in (".md", ".txt", ".json"):
                    try:
                        content = entry.read_text(encoding="utf-8")
                        if len(content) <= 10000:
                            skill["content"] = content
                    except OSError:
                        pass

            skills.append(skill)

        return {"status": "ok", "total": len(skills), "skills": skills}

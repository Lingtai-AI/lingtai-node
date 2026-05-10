"""LingTai Node Contract — the abstract interface for all node runtimes.

This module provides:
- NODE_CONTRACT_VERSION: the current contract version
- validate_node(): check if a node directory satisfies the contract
- CONTRACT_PATH: path to the formal specification document
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

NODE_CONTRACT_VERSION = "2.0.0"

CONTRACT_PATH = Path(__file__).parent / "NODE_CONTRACT.md"

# Runtime → (character_filename, memory_filename, long_term_memory_dir, handover_filename)
RUNTIME_FILE_MAP: dict[str, tuple[str, str, str, str]] = {
    "claude-code": ("CLAUDE.md", "memory.md", "codex", "handover.md"),
    "openai-codex": ("AGENTS.md", "memory.md", "codex", "handover.md"),
    "lingtai": ("lingtai.md", "pad.md", "codex", "handover.md"),
    "hermes": ("identity.md", "goals.md", "memory", "handover.md"),
}


def validate_node(node_dir: Path, *, runtime: str = "claude-code") -> dict[str, Any]:
    """Validate that a node directory satisfies the contract.

    Returns a dict with:
    - valid: bool
    - errors: list of missing/invalid items
    - warnings: list of non-critical issues
    """
    errors: list[str] = []
    warnings: list[str] = []

    node_dir = Path(node_dir)
    if not node_dir.is_dir():
        return {"valid": False, "errors": [f"Node directory does not exist: {node_dir}"], "warnings": []}

    # 1. Required metadata
    agent_json = node_dir / ".agent.json"
    if not agent_json.is_file():
        errors.append("Missing .agent.json")
    else:
        try:
            meta = json.loads(agent_json.read_text(encoding="utf-8"))
            if "name" not in meta:
                warnings.append(".agent.json missing 'name' field")
            if "runtime" not in meta:
                warnings.append(".agent.json missing 'runtime' field")
        except (json.JSONDecodeError, OSError) as e:
            errors.append(f".agent.json is invalid: {e}")

    # 2. Character, memory, and handover files (runtime-specific)
    char_file, mem_file, lt_dir, handover_file = RUNTIME_FILE_MAP.get(runtime, (None, None, None, None))
    if char_file:
        if not (node_dir / char_file).is_file():
            errors.append(f"Missing character file: {char_file}")
    else:
        warnings.append(f"Unknown runtime '{runtime}' — cannot check character file")

    if mem_file:
        if not (node_dir / mem_file).is_file():
            warnings.append(f"Missing memory file: {mem_file}")

    # 3. Mailbox structure
    mailbox = node_dir / "mailbox"
    if not mailbox.is_dir():
        errors.append("Missing mailbox/ directory")
    else:
        for sub in ("inbox", "sent", "archive"):
            if not (mailbox / sub).is_dir():
                errors.append(f"Missing mailbox/{sub}/ directory")

    # 4. Handover file (optional — written before compact/molt, may not exist yet)
    if handover_file:
        if not (node_dir / handover_file).is_file():
            warnings.append(f"Missing {handover_file} (will be created on first compact/molt)")

    # 5. Long-term memory directory
    if lt_dir:
        lt_path = node_dir / lt_dir
        if not lt_path.is_dir():
            warnings.append(f"Missing {lt_dir}/ directory (will be created on first use)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }

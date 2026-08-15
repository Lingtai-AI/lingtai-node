"""Security helpers shared by LingTai node managers."""
from __future__ import annotations

from pathlib import Path


def safe_child(parent: Path, child: str | Path) -> Path:
    """Resolve ``child`` beneath ``parent`` and reject path escapes."""
    parent_path = Path(parent).expanduser().resolve(strict=False)
    child_path = Path(child)
    if child_path.is_absolute():
        raise ValueError(f"path escapes base directory: {child}")

    full = (parent_path / child_path).resolve(strict=False)
    if full != parent_path and parent_path not in full.parents:
        raise ValueError(f"path escapes base directory: {child}")
    return full

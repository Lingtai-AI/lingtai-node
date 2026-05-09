"""Runtime session management for LingTai Node.

Each supported runtime (Claude Code, Codex, Cursor, etc.) has its own
subpackage that implements SessionManager for driving that runtime's CLI.
"""
from .base import SessionManager

__all__ = ["SessionManager"]

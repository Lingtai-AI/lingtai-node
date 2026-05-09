"""LingTai Node MCP server.

Enables non-LingTai runtimes (Claude Code, etc.) to participate in the
LingTai agent network via mailbox-based communication, codex, and library
tools. Maintains a heartbeat to prove liveness and maps runtime-specific
files (CLAUDE.md, memory.md) to LingTai conventions.

Configuration via LINGTAI_NODE_CONFIG env var pointing at a JSON file.
"""
from .server import serve, build_server, load_config

__all__ = [
    "serve",
    "build_server",
    "load_config",
]

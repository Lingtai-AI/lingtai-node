"""LingTai Node MCP server.

Enables non-LingTai runtimes (Claude Code, etc.) to participate in the
LingTai agent network via mailbox-based communication, codex, library,
avatar, covenant, and system tools. Maintains a heartbeat to prove
liveness and maps runtime-specific files (CLAUDE.md, memory.md) to
LingTai conventions.

Configuration via LINGTAI_NODE_CONFIG env var pointing at a JSON file.
"""
from .avatar_manager import AvatarManager
from .covenant_manager import CovenantManager
from .server import serve, build_server, load_config
from .system_manager import SystemManager

__all__ = [
    "AvatarManager",
    "CovenantManager",
    "SystemManager",
    "serve",
    "build_server",
    "load_config",
]

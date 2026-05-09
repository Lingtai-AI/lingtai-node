"""LingTai Node MCP server.

Enables non-LingTai runtimes to participate in the LingTai agent network
by exposing email, codex, library, node_info, mapping, avatar, covenant,
and system tools over MCP/stdio. Maintains a heartbeat file to prove
liveness.

Configuration:
    LINGTAI_NODE_CONFIG — path to a JSON config file (required).

Config schema:

    {
      "agent_dir": "/path/to/agent/working/directory",
      "runtime": "claude-code",
      "agent_name": "my-agent"
    }

If agent_dir is omitted, falls back to LINGTAI_AGENT_DIR env var, then cwd.
If runtime is omitted, defaults to "claude-code".
If agent_name is omitted, defaults to the agent_dir basename.

Env vars injected by the LingTai kernel for LICC:
    LINGTAI_AGENT_DIR — host agent's working directory.
    LINGTAI_MCP_NAME  — this MCP's registry name (typically "node").
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .avatar_manager import AvatarManager
from .avatar_manager import SCHEMA as AVATAR_SCHEMA
from .avatar_manager import DESCRIPTION as AVATAR_DESCRIPTION
from .codex_manager import CodexManager
from .codex_manager import SCHEMA as CODEX_SCHEMA
from .codex_manager import DESCRIPTION as CODEX_DESCRIPTION
from .covenant_manager import CovenantManager
from .covenant_manager import SCHEMA as COVENANT_SCHEMA
from .covenant_manager import DESCRIPTION as COVENANT_DESCRIPTION
from .email_manager import EmailManager
from .email_manager import SCHEMA as EMAIL_SCHEMA
from .email_manager import DESCRIPTION as EMAIL_DESCRIPTION
from .heartbeat import HeartbeatManager
from .contracts import NODE_CONTRACT_VERSION, validate_node
from .library_manager import LibraryManager
from .library_manager import SCHEMA as LIBRARY_SCHEMA
from .library_manager import DESCRIPTION as LIBRARY_DESCRIPTION
from .mapping import MappingManager
from .mapping import SCHEMA as MAPPING_SCHEMA
from .mapping import DESCRIPTION as MAPPING_DESCRIPTION
from .system_manager import SystemManager
from .system_manager import SCHEMA as SYSTEM_SCHEMA
from .system_manager import DESCRIPTION as SYSTEM_DESCRIPTION

log = logging.getLogger("lingtai_node")


CONTRACT_DESCRIPTION = (
    "LingTai Node Contract — the abstract interface that all node runtimes "
    "implement. Use 'read' to see the full contract specification. "
    "Use 'validate' to check if a node directory satisfies the contract."
)

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["read", "validate"],
            "description": (
                "read: return the full contract specification. "
                "validate: check a node directory against the contract."
            ),
        },
        "node_dir": {
            "type": "string",
            "description": "Node directory to validate (for 'validate' action). Defaults to this node's directory.",
        },
    },
    "required": ["action"],
}


_SERVER_INSTRUCTIONS = (
    "lingtai-node: LingTai agent network node for non-LingTai runtimes. "
    "Provides mailbox communication (email tool), knowledge store (codex tool), "
    "skill catalog (library tool), node status (node_info tool), "
    "character/memory file mapping (mapping tool), node spawning (avatar tool), "
    "network contract (covenant tool), inter-node control (system tool), "
    "and node contract specification (contract tool). "
    "Configure via the LINGTAI_NODE_CONFIG env var pointing at a JSON file."
)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Read config from the path in LINGTAI_NODE_CONFIG.

    Path is resolved relative to LINGTAI_AGENT_DIR (or cwd as fallback)
    if not absolute.
    """
    config_path_raw = os.environ.get("LINGTAI_NODE_CONFIG")
    if not config_path_raw:
        raise ValueError(
            "LINGTAI_NODE_CONFIG env var not set — point it at your "
            "node config JSON file"
        )
    config_path = Path(config_path_raw).expanduser()
    if not config_path.is_absolute():
        base = Path(os.environ.get("LINGTAI_AGENT_DIR", os.getcwd()))
        config_path = base / config_path
    if not config_path.is_file():
        raise FileNotFoundError(f"Node config not found: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def _resolve_agent_dir(cfg: dict) -> Path:
    """Determine the agent working directory from config or env."""
    raw = cfg.get("agent_dir") or os.environ.get("LINGTAI_AGENT_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.cwd()


# ---------------------------------------------------------------------------
# Node info helper
# ---------------------------------------------------------------------------

def _build_node_info(
    agent_dir: Path,
    runtime: str,
    agent_name: str,
    heartbeat: HeartbeatManager,
) -> dict:
    """Build the node_info response."""
    # Read .agent.json if present
    agent_meta: dict | None = None
    agent_json = agent_dir / ".agent.json"
    if agent_json.is_file():
        try:
            agent_meta = json.loads(agent_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    hb = heartbeat.read()

    # Validate contract compliance
    validation = validate_node(agent_dir, runtime=runtime)

    return {
        "status": "ok",
        "agent_name": agent_name,
        "agent_dir": str(agent_dir),
        "runtime": runtime,
        "contract_version": NODE_CONTRACT_VERSION,
        "heartbeat": hb,
        "agent_metadata": agent_meta,
        "contract_validation": validation,
    }


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

def build_server(
    email: EmailManager | None,
    codex: CodexManager | None,
    library: LibraryManager | None,
    mapping: MappingManager | None,
    avatar: AvatarManager | None,
    covenant: CovenantManager | None,
    system: SystemManager | None,
    heartbeat: HeartbeatManager | None,
    agent_dir: Path | None,
    runtime: str = "claude-code",
    agent_name: str = "",
) -> Server:
    """Construct the MCP server with all tools."""
    server: Server = Server("lingtai-node", instructions=_SERVER_INSTRUCTIONS)

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="email",
                description=EMAIL_DESCRIPTION,
                inputSchema=EMAIL_SCHEMA,
            ),
            types.Tool(
                name="codex",
                description=CODEX_DESCRIPTION,
                inputSchema=CODEX_SCHEMA,
            ),
            types.Tool(
                name="library",
                description=LIBRARY_DESCRIPTION,
                inputSchema=LIBRARY_SCHEMA,
            ),
            types.Tool(
                name="node_info",
                description=(
                    "Returns information about this node: runtime type, "
                    "heartbeat status, agent metadata."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="mapping",
                description=MAPPING_DESCRIPTION,
                inputSchema=MAPPING_SCHEMA,
            ),
            types.Tool(
                name="avatar",
                description=AVATAR_DESCRIPTION,
                inputSchema=AVATAR_SCHEMA,
            ),
            types.Tool(
                name="covenant",
                description=COVENANT_DESCRIPTION,
                inputSchema=COVENANT_SCHEMA,
            ),
            types.Tool(
                name="system",
                description=SYSTEM_DESCRIPTION,
                inputSchema=SYSTEM_SCHEMA,
            ),
            types.Tool(
                name="contract",
                description=CONTRACT_DESCRIPTION,
                inputSchema=CONTRACT_SCHEMA,
            ),
        ]

    @server.call_tool()
    async def _call_tool(
        name: str, arguments: dict[str, Any],
    ) -> list[types.TextContent]:
        # Update heartbeat on every tool call
        if heartbeat is not None:
            try:
                heartbeat.beat()
            except Exception as e:
                log.warning("Heartbeat update failed: %s", e)

        result: dict

        if name == "email":
            if email is None:
                result = _error("Email manager not initialized")
            else:
                result = await asyncio.to_thread(email.handle, arguments)

        elif name == "codex":
            if codex is None:
                result = _error("Codex manager not initialized")
            else:
                result = await asyncio.to_thread(codex.handle, arguments)

        elif name == "library":
            if library is None:
                result = _error("Library manager not initialized")
            else:
                result = await asyncio.to_thread(library.handle, arguments)

        elif name == "node_info":
            if heartbeat is None or agent_dir is None:
                result = _error("Node not initialized")
            else:
                result = _build_node_info(
                    agent_dir, runtime, agent_name, heartbeat,
                )

        elif name == "mapping":
            if mapping is None:
                result = _error("Mapping manager not initialized")
            else:
                result = await asyncio.to_thread(mapping.handle, arguments)

        elif name == "avatar":
            if avatar is None:
                result = _error("Avatar manager not initialized")
            else:
                result = await asyncio.to_thread(avatar.handle, arguments)

        elif name == "covenant":
            if covenant is None:
                result = _error("Covenant manager not initialized")
            else:
                result = await asyncio.to_thread(covenant.handle, arguments)

        elif name == "system":
            if system is None:
                result = _error("System manager not initialized")
            else:
                result = await asyncio.to_thread(system.handle, arguments)

        elif name == "contract":
            action = arguments.get("action", "read")
            if action == "read":
                try:
                    content = Path(
                        __file__
                    ).resolve().parent / "contracts" / "NODE_CONTRACT.md"
                    result = {
                        "status": "ok",
                        "contract_version": NODE_CONTRACT_VERSION,
                        "content": content.read_text(encoding="utf-8"),
                    }
                except Exception as e:
                    result = _error(f"Failed to read contract: {e}")
            elif action == "validate":
                node_dir = arguments.get("node_dir")
                if not node_dir and agent_dir:
                    node_dir = str(agent_dir)
                if not node_dir:
                    result = _error("node_dir required for validate")
                else:
                    result = validate_node(Path(node_dir), runtime=runtime)
                    result["status"] = "ok"
            else:
                result = _error(f"Unknown contract action: {action}")

        else:
            result = {"error": f"Unknown tool: {name!r}"}

        return [types.TextContent(
            type="text", text=json.dumps(result, ensure_ascii=False),
        )]

    return server


def _error(msg: str) -> dict:
    return {
        "status": "error",
        "error": msg + " — server boot failed. Check stderr for details.",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def serve() -> None:
    """Run the MCP server over stdio."""
    email: EmailManager | None = None
    codex: CodexManager | None = None
    library: LibraryManager | None = None
    mapping_mgr: MappingManager | None = None
    avatar: AvatarManager | None = None
    covenant: CovenantManager | None = None
    system: SystemManager | None = None
    heartbeat: HeartbeatManager | None = None
    agent_dir: Path | None = None
    runtime = "claude-code"
    agent_name = ""

    try:
        cfg = load_config()
        agent_dir = _resolve_agent_dir(cfg)
        agent_dir.mkdir(parents=True, exist_ok=True)
        runtime = cfg.get("runtime", "claude-code")
        agent_name = cfg.get("agent_name", agent_dir.name)

        email = EmailManager(agent_dir, agent_name=agent_name)
        codex = CodexManager(agent_dir)
        library = LibraryManager(agent_dir)
        mapping_mgr = MappingManager(agent_dir, runtime=runtime)
        avatar = AvatarManager(agent_dir)
        covenant = CovenantManager(agent_dir, agent_name=agent_name)
        system = SystemManager(agent_dir, agent_name=agent_name)
        heartbeat = HeartbeatManager(agent_dir, runtime=runtime)
        heartbeat.start()
        log.info(
            "lingtai-node initialized: agent=%s dir=%s runtime=%s",
            agent_name, agent_dir, runtime,
        )
    except Exception as e:
        log.error(
            "Initialization failed; tool calls will return errors: %s", e,
        )

    server = build_server(
        email=email,
        codex=codex,
        library=library,
        mapping=mapping_mgr,
        avatar=avatar,
        covenant=covenant,
        system=system,
        heartbeat=heartbeat,
        agent_dir=agent_dir,
        runtime=runtime,
        agent_name=agent_name,
    )

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        if heartbeat is not None:
            try:
                heartbeat.stop()
            except Exception:
                pass

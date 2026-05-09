"""LingTai Node MCP server.

Enables non-LingTai runtimes to participate in the LingTai agent network
by exposing email, codex, library, node_info, and mapping tools over
MCP/stdio. Maintains a heartbeat file to prove liveness.

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

from .codex_manager import CodexManager
from .codex_manager import SCHEMA as CODEX_SCHEMA
from .codex_manager import DESCRIPTION as CODEX_DESCRIPTION
from .email_manager import EmailManager
from .email_manager import SCHEMA as EMAIL_SCHEMA
from .email_manager import DESCRIPTION as EMAIL_DESCRIPTION
from .heartbeat import HeartbeatManager
from .library_manager import LibraryManager
from .library_manager import SCHEMA as LIBRARY_SCHEMA
from .library_manager import DESCRIPTION as LIBRARY_DESCRIPTION
from .mapping import MappingManager
from .mapping import SCHEMA as MAPPING_SCHEMA
from .mapping import DESCRIPTION as MAPPING_DESCRIPTION

log = logging.getLogger("lingtai_node")


_SERVER_INSTRUCTIONS = (
    "lingtai-node: LingTai agent network node for non-LingTai runtimes. "
    "Provides mailbox communication (email tool), knowledge store (codex tool), "
    "skill catalog (library tool), node status (node_info tool), and "
    "character/memory file mapping (mapping tool). "
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

    return {
        "status": "ok",
        "agent_name": agent_name,
        "agent_dir": str(agent_dir),
        "runtime": runtime,
        "heartbeat": hb,
        "agent_metadata": agent_meta,
    }


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

def build_server(
    email: EmailManager | None,
    codex: CodexManager | None,
    library: LibraryManager | None,
    mapping: MappingManager | None,
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

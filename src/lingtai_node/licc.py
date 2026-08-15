"""LICC v1 client helper — push events into the host agent's inbox.

Vendored verbatim into each LingTai MCP server. The kernel side of this
contract lives in lingtai-kernel/src/lingtai/core/mcp/inbox.py.

Two env vars must be set by the kernel when spawning this MCP:
    LINGTAI_AGENT_DIR  — absolute path of the agent's working directory.
    LINGTAI_MCP_NAME   — the MCP's registry name.

Both are injected automatically by lingtai-kernel's MCP loader. If they
are missing (e.g., running this MCP outside LingTai), push_inbox_event
becomes a no-op and logs a warning.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

LICC_VERSION = 1
INBOX_DIRNAME = ".mcp_inbox"
TMP_SUFFIX = ".json.tmp"


def push_inbox_event(
    sender: str,
    subject: str,
    body: str,
    *,
    metadata: dict | None = None,
    wake: bool = True,
) -> bool:
    """Write a LICC event into the host agent's inbox.

    Returns True on success, False if the env vars are missing or the
    write fails. Never raises — designed to be safe inside listener
    callbacks where exceptions would silently kill the listener thread.
    """
    agent_dir = os.environ.get("LINGTAI_AGENT_DIR")
    mcp_name = os.environ.get("LINGTAI_MCP_NAME")

    if not agent_dir or not mcp_name:
        log.warning(
            "LICC: LINGTAI_AGENT_DIR and/or LINGTAI_MCP_NAME not set; "
            "running outside a LingTai host? Event dropped: %s / %s",
            sender, subject,
        )
        return False

    event = {
        "licc_version": LICC_VERSION,
        "from": sender,
        "subject": subject,
        "body": body,
        "metadata": metadata or {},
        "wake": wake,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        target_dir = _resolve_target_dir(agent_dir, mcp_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        event_id = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
        tmp = target_dir / f"{event_id}{TMP_SUFFIX}"
        final = target_dir / f"{event_id}.json"
        # Write + fsync + atomic rename so the host poller never sees a
        # half-written file.
        text = json.dumps(event, ensure_ascii=False)
        with tmp.open("w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        tmp.rename(final)
        return True
    except OSError as e:
        log.error("LICC: failed to write event for %s: %s", mcp_name, e)
        return False


def _resolve_target_dir(agent_dir: str, mcp_name: str) -> Path:
    agent_path = Path(agent_dir).expanduser()
    if not agent_path.is_absolute():
        raise OSError("LINGTAI_AGENT_DIR must be absolute")

    project_root_raw = os.environ.get("LINGTAI_PROJECT_DIR")
    project_root = Path(project_root_raw).expanduser() if project_root_raw else Path.cwd()
    project_root = project_root.resolve(strict=False)
    agent_path = agent_path.resolve(strict=False)
    if agent_path != project_root and project_root not in agent_path.parents:
        raise OSError("LINGTAI_AGENT_DIR escapes project root")

    if Path(mcp_name).name != mcp_name:
        raise OSError("LINGTAI_MCP_NAME must be a single path segment")

    return agent_path / INBOX_DIRNAME / mcp_name

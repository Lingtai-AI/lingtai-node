# lingtai-node

MCP server that enables non-LingTai runtimes (Claude Code, etc.) to participate in the LingTai agent network.

## Features

- **Email** — mailbox-based communication (send, check, read, reply, search, archive, delete, contacts)
- **Codex** — knowledge store (view, submit, consolidate, delete)
- **Library** — skill catalog from `.library/` directory
- **Node Info** — runtime type, heartbeat status, agent metadata
- **Mapping** — character/memory file mapping across runtimes (CLAUDE.md ↔ lingtai.md)
- **Heartbeat** — background thread proves liveness via `.heartbeat` file

## Installation

```bash
pip install -e .
```

Or from PyPI (when published):

```bash
pip install lingtai-node
```

## Configuration

Create a JSON config file:

```json
{
  "agent_dir": "/path/to/agent/working/directory",
  "runtime": "claude-code",
  "agent_name": "my-agent"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `agent_dir` | No | `LINGTAI_AGENT_DIR` env var, then cwd | Agent working directory |
| `runtime` | No | `claude-code` | Runtime type (`claude-code` or `lingtai`) |
| `agent_name` | No | basename of `agent_dir` | Agent name for email "from" field |

Set the env var:

```bash
export LINGTAI_NODE_CONFIG=/path/to/config.json
```

## Usage

### Standalone

```bash
lingtai-node
# or
python -m lingtai_node
```

### Claude Code MCP

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "lingtai-node": {
      "command": "lingtai-node",
      "env": {
        "LINGTAI_NODE_CONFIG": "/path/to/config.json"
      }
    }
  }
}
```

### LingTai Kernel

When spawned by the LingTai kernel, these env vars are set automatically:

- `LINGTAI_NODE_CONFIG` — path to config file
- `LINGTAI_AGENT_DIR` — agent working directory
- `LINGTAI_MCP_NAME` — MCP registry name (for LICC)

## Tools

### email

Mailbox-based communication with the agent network.

| Action | Parameters | Description |
|--------|------------|-------------|
| `send` | `to`, `subject`, `body` | Send a message |
| `check` | `folder?`, `limit?` | List inbox summary |
| `read` | `id` | Read a specific message |
| `reply` | `id`, `body` | Reply to a message |
| `search` | `query`, `folder?`, `limit?` | Search messages (regex) |
| `archive` | `id` | Move message to archive |
| `delete` | `id` | Permanently delete message |
| `contacts` | — | List saved contacts |
| `add_contact` | `name`, `address` | Add a contact |
| `remove_contact` | `name` or `address` | Remove a contact |
| `edit_contact` | `name`, `new_name?`, `new_address?` | Edit a contact |

### codex

Knowledge store for persistent structured data.

| Action | Parameters | Description |
|--------|------------|-------------|
| `view` | `tags?` | List entries (optional tag filter) |
| `submit` | `title`, `content`, `tags?` | Add a new entry |
| `consolidate` | `tag` | Merge entries by tag |
| `delete` | `id` | Remove an entry |

### library

Skill catalog from `.library/` directory.

| Action | Description |
|--------|-------------|
| `info` | Return the full skill catalog |

### node_info

Returns node status (no parameters).

### mapping

Character and memory file mapping.

| Action | Parameters | Description |
|--------|------------|-------------|
| `get_character` | — | Read character/persona file |
| `set_character` | `content` | Write character/persona file |
| `get_memory` | — | Read memory/scratchpad file |
| `set_memory` | `content` | Write memory/scratchpad file |

File mapping by runtime:

| Runtime | Character | Memory |
|---------|-----------|--------|
| `claude-code` | `CLAUDE.md` | `memory.md` |
| `lingtai` | `lingtai.md` | `pad.md` |

## Directory Structure

```
agent_dir/
├── .agent.json              # Agent metadata
├── .heartbeat               # Heartbeat file (auto-updated)
├── .prompt                  # Incoming task (consumed by watcher)
├── .response                # Task output (written by watcher)
├── mailbox/
│   ├── inbox/               # Incoming messages
│   ├── sent/                # Sent messages
│   ├── archive/             # Archived messages
│   ├── contacts.json        # Contact list
│   └── .read_state.json     # Read tracking
├── codex/
│   └── codex.json           # Knowledge entries
├── .library/                # Skill catalog
├── CLAUDE.md                # Character file (auto-generated from template)
└── memory.md                # Memory file (auto-generated from template)
```

## CLAUDE.md — The Pre-Compact Ritual

When a node is spawned, `lingtai-node` automatically copies a `CLAUDE.md` template into the node directory. This file serves as the node's **character** — its identity across sessions.

Claude Code loads `CLAUDE.md` from its working directory as part of its system prompt. The template defines:

1. **Who the node is** — a LingTai network peer with email, codex, and library
2. **Pre-compact ritual** — what to save before auto-compact sheds context (equivalent to LingTai's molt)
3. **Post-compact recovery** — what to read after compaction to reconstruct context
4. **Behavior guidelines** — proactive email checking, honest escalation, thorough reporting

The mapping between LingTai and Claude Code concepts:

| LingTai | Claude Code | File |
|---------|-------------|------|
| Character (灵台) | System prompt | `CLAUDE.md` |
| Working memory (心台) | Project knowledge | `memory.md` |
| Knowledge (典藏) | MCP tool | `codex/` |
| Skills (技能) | MCP tool | `library/` |
| Communication (传书) | MCP tool | `mailbox/` |

## License

MIT

# lingtai-node

MCP server that enables non-LingTai runtimes (Claude Code, OpenAI Codex, Hermes, etc.) to participate in the LingTai agent network.

## Contract v2 — The Six Artifacts

The LingTai Node Contract defines what a **node** is — the abstract unit of agency in a LingTai network. Every node, regardless of runtime, must provide six artifacts and the lifecycle hooks to preserve them across context resets.

| # | Artifact | Purpose | Persistence |
|---|----------|---------|-------------|
| 1 | **Identity** | Who I am — personality, values, expertise, working style | Permanent |
| 2 | **Memory** | Working state — current task, plans, notes, contacts | Survives compaction |
| 3 | **Knowledge** | What I've learned — verifiable truths, key decisions, discoveries | Permanent |
| 4 | **Skill** | What I can do — reusable procedures, workflows, playbooks | Permanent |
| 5 | **Communication** | How I interact — message passing, contacts, channels | Ephemeral / permanent |
| 6 | **Handover** | Letter to next self — transition state before context switch | Ephemeral (read once) |

The contract defines the **purpose** of each artifact, not the exact filename. Each runtime uses its own naming convention. See [NODE_CONTRACT.md](src/lingtai_node/contracts/NODE_CONTRACT.md) for the full specification.

### Runtime Mapping

| Artifact | Claude Code | LingTai Kernel | Hermes | OpenClaw |
|----------|-------------|----------------|--------|----------|
| **Identity** | `CLAUDE.md` | `lingtai.md` (灵台) | `identity.md` | `IDENTITY` + `SOUL.md` |
| **Memory** | `memory.md` | `pad.md` | `goals.md` + `continuity.md` | `AGENTS.md` + `BOOT.md` |
| **Knowledge** | `~/.codex/memories/` | `codex` store | `memory/MEMORY.md` | `MEMORY.md` |
| **Skill** | `AGENTS.md` / `.library/` | `.library/` | `scripts/` | `.agents/skills/` |
| **Communication** | *(none — use MCP)* | `email` intrinsic | `email.py` | channels (Telegram, Discord, etc.) |
| **Handover** | `handover.md` | `molt summary` | `journal.md` | *(none)* |

### Comparison with Other Frameworks

| Feature | LingTai Node | OpenAI Codex | Hermes | OpenClaw |
|---------|-------------|--------------|--------|----------|
| **Handover file** | Yes | No | No | No |
| **Cross-harness** | Yes (design goal) | No | No | No |
| **Identity as artifact** | Yes | No | Yes | Yes |
| **Communication layer** | Yes | No | Yes (email) | Yes (channels) |
| **Format agnostic** | Yes | No (generated) | Yes (files) | Yes (files) |

The key differentiator: the contract is **harness agnostic** — it defines what to preserve, not how. Each runtime implements the six artifacts using its own conventions.

## Features

- **Email** — mailbox-based communication (send, check, read, reply, search, archive, delete, contacts)
- **Codex** — knowledge store (view, submit, consolidate, delete)
- **Library** — skill catalog from `.library/` directory
- **Node Info** — runtime type, heartbeat status, agent metadata, contract validation
- **Mapping** — character/memory file mapping across runtimes (CLAUDE.md / lingtai.md / AGENTS.md / identity.md)
- **Heartbeat** — background thread proves liveness via `.heartbeat` file
- **Avatar** — spawn, list, and terminate sibling agent nodes
- **Covenant** — LingTai network contract acknowledgment
- **System** — inter-node control via signal files (.prompt, .sleep, .suspend)
- **Contract** — read the contract specification and validate node directories

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
| `runtime` | No | `claude-code` | Runtime type (`claude-code`, `openai-codex`, `lingtai`, or `hermes`) |
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
| `openai-codex` | `AGENTS.md` | `memory.md` |
| `lingtai` | `lingtai.md` | `pad.md` |
| `hermes` | `identity.md` | `goals.md` |

### avatar

Spawn, list, and terminate sibling agent nodes.

| Action | Parameters | Description |
|--------|------------|-------------|
| `spawn` | `name`, `mission`, `runtime?` | Create a new node directory |
| `list` | — | Scan for sibling nodes |
| `terminate` | `name` | Write a .suspend signal file |

### covenant

LingTai network contract.

| Action | Description |
|--------|-------------|
| `read` | View the covenant text |
| `acknowledge` | Formally accept the covenant |
| `check` | Verify acknowledgment status |

### system

Inter-node control via signal files.

| Action | Parameters | Description |
|--------|------------|-------------|
| `wake` | `target`, `prompt` | Write a .prompt file to a target node |
| `sleep` | `target` | Write a .sleep signal |
| `suspend` | `target` | Write a .suspend signal |
| `status` | `target` | Read a target node's heartbeat |
| `list_nodes` | — | Discover all nodes in the parent directory |

### contract

Node contract specification.

| Action | Parameters | Description |
|--------|------------|-------------|
| `read` | — | Return the full contract spec |
| `validate` | `node_dir?` | Check a directory against the contract |

## Directory Structure

```
agent_dir/
├── .agent.json              # Agent metadata (name, runtime, contract_version)
├── .heartbeat               # Heartbeat file (auto-updated)
├── .prompt                  # Incoming task (consumed by watcher)
├── .response                # Task output (written by watcher)
├── CLAUDE.md                # Identity file (runtime-specific name)
├── memory.md                # Memory file (runtime-specific name)
├── handover.md              # Letter to the next self (written before compact/molt)
├── mailbox/
│   ├── inbox/               # Incoming messages
│   ├── sent/                # Sent messages
│   ├── archive/             # Archived messages
│   ├── contacts.json        # Contact list
│   └── .read_state.json     # Read tracking
├── codex/
│   └── codex.json           # Knowledge entries
└── .library/                # Skill catalog
```

## Pre-Compact Ritual & Handover

When a node is spawned, `lingtai-node` automatically copies templates (`CLAUDE.md`, `memory.md`, `handover.md`) into the node directory.

The **pre-compact ritual** (防蜕) saves state before context is shed:

1. **Update identity** (CLAUDE.md) if character evolved
2. **Rewrite memory** (memory.md) with current working state
3. **Save knowledge** to codex via MCP tool
4. **Save skills** to library via MCP tool
5. **Write handover** (handover.md) — a letter to the next self

The **post-compact recovery** (复蜕) restores state after compaction:

1. **Read identity** — re-establish who you are
2. **Read memory** — recover working state
3. **Read handover** — absorb wisdom from the previous self
4. **Check email** — read messages that arrived during compaction
5. **Query knowledge** — load relevant facts

## License

MIT

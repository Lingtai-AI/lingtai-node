# LingTai Node Contract

> *"One Lingtai, one self, many avatars."*
> This contract defines what a **node** is — the abstract unit of agency in a LingTai network.
> Each runtime provides its own implementation of this contract, but the semantic structure is universal.

## 1. What Is a Node

A node is an autonomous agent process that:

- Has an **identity** that persists across sessions (character)
- Maintains **working memory** that carries state forward (memory)
- Accumulates **knowledge** over time (codex)
- Builds **skills** through experience (library)
- **Communicates** with other nodes in the network (email)

Every node, regardless of runtime, must provide these five stores and the lifecycle hooks to preserve them across context resets.

## 2. The Five Stores

| Store | Purpose | Persistence | Semantics |
|-------|---------|-------------|-----------|
| **Character** | Identity — who the node is, what it knows, how it works | Survives everything | Read on every session start; written when identity evolves |
| **Memory** | Working state — current task, plans, notes, contacts | Survives compaction/molt | Read on every session start; rewritten freely |
| **Knowledge** (Codex) | Permanent facts — verifiable truths, key discoveries, critical decisions | Permanent but bounded | Queried on demand; one fact per entry |
| **Skills** (Library) | Reusable procedures — workflows, playbooks, accumulated competence | Permanent, shareable | Loaded when needed; one procedure per skill |
| **Communication** (Email) | Message passing — inter-node coordination | Ephemeral (inbox) / permanent (archive) | Checked at session start; replied on same channel |

## 3. Lifecycle Hooks

Every node must implement two lifecycle hooks:

### 3.1 Pre-Compact Ritual (防蜕)

Called **before** the runtime sheds conversation context. The node must save all valuable state to its durable stores.

**Required actions:**
1. **Update character** if identity evolved during this session
2. **Rewrite memory** with current working state
3. **Submit knowledge** to codex for any new verifiable facts
4. **Save skills** to library for any new reusable procedures

**When to call:**
- The runtime signals that compaction is imminent (e.g., Claude Code auto-compact, LingTai molt warning)
- The node decides to proactively save (e.g., after learning something significant)

### 3.2 Post-Compact Recovery (复蜕)

Called **after** the runtime sheds conversation context. The node must reconstruct its situation from durable stores.

**Required actions:**
1. **Read character** — re-establish identity
2. **Read memory** — recover working state
3. **Check communication** — read any messages that arrived during/after compaction
4. **Query knowledge** — load relevant codex entries for the current task

**When to call:**
- At the start of every new session (automatic)
- After compaction/molt (automatic)

## 4. Runtime Mapping

Each runtime implements the five stores and two hooks using its own conventions:

| Concept | Claude Code | LingTai Kernel | Generic MCP |
|---------|-------------|----------------|-------------|
| Character | `CLAUDE.md` (auto-loaded as system prompt) | `lingtai.md` (via psyche intrinsic) | `<runtime>.md` (via mapping tool) |
| Memory | `memory.md` (project knowledge) | `pad.md` (via psyche intrinsic) | `memory.md` (via mapping tool) |
| Knowledge | `codex/` directory (via MCP `codex` tool) | codex store (via `codex` capability) | `codex/` (via MCP `codex` tool) |
| Skills | `.library/` directory (via MCP `library` tool) | `.library/` (via `library` capability) | `.library/` (via MCP `library` tool) |
| Communication | `mailbox/` directory (via MCP `email` tool) | mailbox (via `email` intrinsic) | `mailbox/` (via MCP `email` tool) |
| Pre-compact | Rules in `CLAUDE.md` | `psyche(context, molt)` | Rules in `<runtime>.md` |
| Post-compact | Auto (CLAUDE.md + memory.md loaded) | Auto (pad + lingtai reloaded) | Auto (runtime-specific) |

## 5. Directory Structure

Every node must have this directory layout:

```
node_dir/
├── .agent.json              # Node metadata (name, runtime, parent, birth time)
├── .heartbeat               # Liveness signal (auto-updated by runtime)
├── <character-file>         # Runtime-specific character file (see mapping)
├── <memory-file>            # Runtime-specific memory file (see mapping)
├── mailbox/
│   ├── inbox/               # Incoming messages
│   ├── sent/                # Sent messages
│   ├── archive/             # Archived messages
│   └── contacts.json        # Saved contacts
├── codex/
│   └── codex.json           # Knowledge entries
└── .library/                # Skill catalog (optional at spawn)
```

The character and memory filenames vary by runtime — see the mapping table above. The mailbox, codex, and library structures are universal.

## 6. Implementation Contract

A runtime implementation MUST:

1. **Create** the directory structure and character/memory files on node spawn
2. **Load** the character file at the start of every session
3. **Load** the memory file at the start of every session
4. **Provide** tools for reading/writing to codex, library, and mailbox
5. **Implement** the pre-compact ritual (either via file rules or explicit hook)
6. **Implement** the post-compact recovery (either automatic or explicit hook)
7. **Maintain** the heartbeat file to prove liveness

A runtime implementation SHOULD:

1. **Auto-detect** compaction events and trigger the pre-compact ritual
2. **Validate** the node directory structure on startup
3. **Copy** templates (character, memory) from the package on spawn
4. **Support** the standard `.prompt` / `.response` file protocol for task dispatch

## 7. Versioning

This contract is versioned. The version is stored in `.agent.json`:

```json
{
  "contract_version": "1.0.0",
  "runtime": "claude-code",
  "name": "my-node"
}
```

Breaking changes to the directory structure, store semantics, or lifecycle hooks will increment the major version. New features (optional stores, new hooks) increment the minor version.

---

*This contract is part of the `lingtai-node` package. It defines the abstract interface that all LingTai node runtimes must implement.*

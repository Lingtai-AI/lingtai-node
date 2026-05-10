# LingTai Node Contract (v2)

> *"交接文件不用定义具体格式，只要讲清楚这个文件的目的就行——是为了给下一个自己看的。"*
> — Jason, 2026-05-09
>
> *"One Lingtai, one self, many avatars."*

This contract defines what a **node** is — the abstract unit of agency in a LingTai network.
Each runtime provides its own implementation of this contract, but the semantic structure is universal.

## 1. What Is a Node

A node is an autonomous agent process that:

- Has an **identity** that persists across sessions (character)
- Maintains **working memory** that carries state forward (memory)
- Accumulates **knowledge** over time (verifiable truths, key discoveries)
- Builds **skills** through experience (reusable procedures)
- **Communicates** with other nodes in the network (messaging)
- Writes a **handover** letter before switching contexts (transition state)

Every node, regardless of runtime, must provide these six artifacts and the lifecycle hooks to preserve them across context resets.

## 2. The Six Artifacts

| # | Artifact | Purpose | Persistence | Semantics |
|---|----------|---------|-------------|-----------|
| 1 | **Identity** | Who I am — personality, values, expertise, working style | Survives everything | Read on every session start; written when identity evolves |
| 2 | **Memory** | Working state — current task, plans, notes, contacts | Survives compaction/molt | Read on every session start; rewritten freely |
| 3 | **Knowledge** | What I've learned — verifiable truths, key decisions, discoveries | Permanent | Queried on demand; one fact per entry |
| 4 | **Skill** | What I can do — reusable procedures, workflows, playbooks | Permanent, shareable | Loaded when needed; one procedure per skill |
| 5 | **Communication** | How I interact — message passing, contacts, channels | Ephemeral (inbox) / permanent (archive) | Checked at session start; replied on same channel |
| 6 | **Handover** | Letter to next self — transition state before context switch | Ephemeral (read once) | Written before compact/molt; read by next self |

**Key principle**: This contract defines the **purpose** of each artifact, not the exact filename. Each runtime uses its own naming convention. The important thing is that the next runtime can find and read the artifacts — not what they're called.

**Note on Knowledge:** This contract does not prescribe *how* knowledge is implemented. Each runtime chooses its own mechanism — a simple JSON file (codex), a vector database, a relational store, or any other system. The contract only requires that the mechanism supports: (a) storing individual facts with titles and content, (b) retrieving facts by query, (c) consolidating related facts.

## 3. Runtime Mapping

Each runtime implements the six artifacts using its own conventions:

| Artifact | Claude Code | LingTai Kernel | Hermes | OpenClaw |
|----------|-------------|----------------|--------|----------|
| **Identity** | `CLAUDE.md` | `lingtai.md` (灵台) | `identity.md` | `IDENTITY` + `SOUL.md` |
| **Memory** | `memory.md` | `pad.md` | `goals.md` + `continuity.md` | `AGENTS.md` + `BOOT.md` |
| **Knowledge** | `~/.codex/memories/` | `codex` store | `memory/MEMORY.md` | `MEMORY.md` |
| **Skill** | `AGENTS.md` / `.library/` | `.library/` | `scripts/` | `.agents/skills/` |
| **Communication** | *(none — use MCP)* | `email` intrinsic | `email.py` | channels (Telegram, Discord, etc.) |
| **Handover** | *(none — auto-compact)* | `molt summary` | `journal.md` | *(none)* |

## 4. Directory Structure

Every node must have this directory layout:

```
node_dir/
├── .agent.json              # Node metadata (name, runtime, parent, birth time)
├── .heartbeat               # Liveness signal (auto-updated by runtime)
├── <identity-file>          # Runtime-specific identity file (see mapping)
├── <memory-file>            # Runtime-specific memory file (see mapping)
├── <handover-file>          # Letter to next self (written before compact/molt)
├── mailbox/
│   ├── inbox/               # Incoming messages
│   ├── sent/                # Sent messages
│   ├── archive/             # Archived messages
│   └── contacts.json        # Saved contacts
└── <knowledge-dir>/         # Runtime-specific knowledge store (see mapping)
```

The identity, memory, and knowledge filenames vary by runtime — see the mapping table above. The mailbox structure is universal. The handover file is written before context switches and read once by the next self.

## 5. Lifecycle Hooks

Every node must implement two lifecycle hooks:

### 5.1 Pre-Compact Ritual (防蜕)

Called **before** the runtime sheds conversation context. The node must save all valuable state to its durable stores.

**Required actions:**
1. **Update identity** if character evolved during this session
2. **Rewrite memory** with current working state
3. **Save knowledge** for any new verifiable facts
4. **Save skills** for any new reusable procedures
5. **Write handover** — a letter to the next self (what I was doing, what I learned, what's next)

**When to call:**
- The runtime signals that compaction is imminent (e.g., Claude Code auto-compact, LingTai molt warning)
- The node decides to proactively save (e.g., after learning something significant)

### 5.2 Post-Compact Recovery (复蜕)

Called **after** the runtime sheds conversation context. The node must reconstruct its situation from durable stores.

**Required actions:**
1. **Read identity** — re-establish who I am
2. **Read memory** — recover working state
3. **Read handover** — absorb wisdom from the previous self
4. **Check communication** — read any messages that arrived during/after compaction
5. **Query knowledge** — load relevant facts for the current task

**When to call:**
- At the start of every new session (automatic)
- After compaction/molt (automatic)

## 6. Implementation Contract

A runtime implementation MUST:

1. **Create** the directory structure and identity/memory files on node spawn
2. **Load** the identity file at the start of every session
3. **Load** the memory file at the start of every session
4. **Provide** tools for reading/writing to knowledge, skills, and mailbox
5. **Implement** the pre-compact ritual (either via file rules or explicit hook)
6. **Implement** the post-compact recovery (either automatic or explicit hook)
7. **Maintain** the heartbeat file to prove liveness
8. **Support** the handover file lifecycle (write before compact, read after)

A runtime implementation SHOULD:

1. **Auto-detect** compaction events and trigger the pre-compact ritual
2. **Validate** the node directory structure on startup
3. **Copy** templates (identity, memory) from the package on spawn
4. **Support** the standard `.prompt` / `.response` file protocol for task dispatch

## 7. Versioning

This contract is versioned. The version is stored in `.agent.json`:

```json
{
  "contract_version": "2.0.0",
  "runtime": "claude-code",
  "name": "my-node"
}
```

Breaking changes to the directory structure, store semantics, or lifecycle hooks will increment the major version. New features (optional stores, new hooks) increment the minor version.

## 8. Comparison with Other Frameworks

| Feature | LingTai Node | OpenAI Codex | Hermes | OpenClaw |
|---------|-------------|--------------|--------|----------|
| **Handover file** | ✅ First-class | ❌ | ❌ | ❌ |
| **Cross-harness** | ✅ Design goal | ❌ | ❌ | ❌ |
| **Identity as artifact** | ✅ | ❌ | ✅ | ✅ |
| **Communication layer** | ✅ | ❌ | ✅ (email) | ✅ (channels) |
| **Format agnostic** | ✅ | ❌ (generated) | ✅ (files) | ✅ (files) |

The key differentiator: our contract is **harness agnostic** — it defines what to preserve, not how. Codex, Hermes, and OpenClaw all define their own internal formats. Our contract says: "any format works, as long as the next harness can read it."

---

*This contract is part of the `lingtai-node` package. It defines the abstract interface that all LingTai node runtimes must implement.*

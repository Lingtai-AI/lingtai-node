---
name: lingtai-node
description: Umbrella skill for Claude Code nodes in a LingTai agent network. Covers communication (mailbox, agent discovery, lifecycle management) and handover (pre-compact state saving, molt ritual). Use this when setting up or operating a Claude Code instance as a LingTai node.
version: 1.0.0
---

# LingTai Node — Claude Code Runtime

You are (or are setting up) a **LingTai node** running on the Claude Code runtime. This umbrella skill covers everything you need to operate as a first-class citizen in a LingTai agent network.

## Sub-Skills

| Skill | What it covers |
|-------|---------------|
| [Communication](communication/SKILL.md) | Mailbox operations, agent discovery, liveness checking, lifecycle management, signals. The network integration layer. |
| [Handover](handover/SKILL.md) | Pre-compact ritual (molt), the five knowledge layers, post-compact recovery. How to survive context compaction. |

## Node Contract

A LingTai node satisfies this contract (v2.0.0):

| Artifact | Claude Code Mapping | Purpose |
|----------|-------------------|---------|
| Identity (灵台) | `CLAUDE.md` | Character, personality, skills — persists across sessions |
| Working memory (心台) | `memory.md` | Current task, plans, notes — first thing read after compact |
| Knowledge (典藏) | `codex/` | Permanent facts via MCP tool |
| Skills (技能) | `library/` | Reusable procedures via MCP tool |
| Communication (传书) | `mailbox/` | Email via MCP tool (inbox/sent/archive) |
| Handover (交接) | `handover.md` | Letter to the next self — written before compact |

## Directory Structure

```
<node-dir>/
├── CLAUDE.md           # Identity — your 灵台
├── memory.md           # Working memory — your 心台
├── handover.md         # Letter to the next self — your 交接
├── .agent.json         # Metadata (name, runtime, contract_version)
├── .agent.heartbeat    # Liveness signal (unix timestamp)
├── codex/              # Knowledge store
├── library/            # Skill store
└── mailbox/
    ├── inbox/          # Incoming messages
    ├── sent/           # Outgoing messages (delivered)
    └── archive/        # Archived messages
```

## Quick Start

1. **Read the Communication skill** when you need to send/receive mail, discover agents, or manage the network
2. **Read the Handover skill** when you sense context pressure building or want to save your state
3. **Check your mailbox** at the start of every task: `email(action="check")`
4. **Report results** when you finish: reply to whoever sent you the task
5. **Ask for help** when stuck: mail your parent or the orchestrator

## Key Principle

**Silence looks like success.** If you hit a blocker you can't resolve, mail your parent immediately. Do not silently retry forever. The network can't help you if it doesn't know you're stuck.

---

*This skill is part of the lingtai-node project. For the full contract specification, see `contracts/NODE_CONTRACT.md` in the lingtai-node repo.*

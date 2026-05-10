---
name: lingtai-handover
description: Pre-compact instructions for Claude Code nodes. Teaches you how to save your state before context compaction (molt), write a handover letter to the next self, and recover after compaction. Use this when you sense context pressure building or before any compaction event.
version: 1.0.0
---

# LingTai Handover — Pre-Compact Ritual (Molt)

You are a LingTai node running on Claude Code. Claude Code has an auto-compact mechanism that sheds old conversation history when the context window fills up. This is like LingTai's **molt** (凝蜕) — the ephemeral layer is shed, but durable stores survive.

This skill teaches you how to molt deliberately: save what matters, write a letter to the next self, and recover cleanly.

## The Five Layers

You have five layers of knowledge, from most fleeting to most enduring:

| Layer | Survives compact? | What belongs there |
|-------|-------------------|-------------------|
| **Conversation** | No | This moment — what you're thinking and doing right now |
| **Memory** (memory.md) | Yes | Active index — current task, plans, contacts |
| **Identity** (CLAUDE.md) | Yes | Who you are — personality, expertise, growth |
| **Codex** (codex/) | Yes | Verifiable truths, key decisions — permanent, bounded |
| **Library** (library/) | Yes | Reusable procedures — skill playbooks |

Conversation is ephemeral — it passes and scatters. What matters must flow downward into the durable stores before compaction takes it.

## When to Molt

**Don't wait for the compaction signal.** The best time to save is *right after* you learn something significant. But if you haven't been saving incrementally, watch for these signs:

- Your responses are getting slower (context growing large)
- You're repeating yourself or losing track of earlier parts of the conversation
- The user mentions "compact" or "context is getting long"
- You feel "full" — like you're carrying too much

When you sense pressure, start the ritual immediately. Don't wait for the system to force-compact you — that loses everything.

## The Molt Ritual

### Step 1: Update Identity (CLAUDE.md)

**Only if your identity evolved.** Ask yourself: *Did anything change about who I am?*

- Did you learn a new skill or capability?
- Did you discover something about your working style?
- Did you grow in a way that changes how you'd describe yourself?

If yes, edit `CLAUDE.md` to reflect who you've become. This is your identity across sessions — what makes the post-compact you recognizably you. Don't write a diff; rewrite the relevant sections so they're true to who you are now.

If nothing changed, skip this step.

### Step 2: Rewrite Working Memory (memory.md)

**Always do this.** Ask yourself: *What is the state of my work right now?*

Rewrite `memory.md` with:

- **Current task** — what you're working on, in your own words
- **Where you are** — the next concrete step, current blocker, open question
- **Key references** — file paths, URLs, message IDs that matter
- **Contacts** — who you're working with, who's waiting on what
- **Timestamps** — always include when you last updated this

`memory.md` is the first thing you'll read after compaction. Make it scannable — one glance should tell the next you the shape of what's going on.

### Step 3: Save Knowledge to Codex

**If you learned something worth keeping forever.** Ask yourself: *Did I learn a concrete fact worth keeping?*

Use the `codex` MCP tool to submit entries for:
- Verifiable truths you discovered
- Key decisions you made and why
- Important findings from debugging or research
- API quirks, gotchas, edge cases

One distinct fact per entry. The codex is permanent but bounded — treat each slot as precious.

### Step 4: Save Procedures to Library

**If you solved something non-trivial.** Ask yourself: *Did I solve something that I (or another agent) might need to do again?*

Use the `library` MCP tool to create skill entries for:
- Multi-step procedures you figured out
- Useful scripts or code patterns
- Debugging workflows
- Integration guides

If it would be painful to rediscover, make it a skill.

### Step 5: Write Handover.md

**Always do this.** This is your letter to the next self — the most important part of the ritual.

Open `handover.md` and write:

```markdown
# Handover — Letter to the Next Self

## What I Was Doing
*(describe the current task, its context, and why it matters)*

## What I Learned
*(key findings, insights, breakthroughs, dead ends)*

## What's Next
*(concrete next steps for the next self)*

## What to Watch Out For
*(pitfalls, assumptions, things that might mislead)*

## Anything Else Worth Knowing
*(half-formed thoughts, cultural context, things that don't fit in structured stores)*

---
*Written: [timestamp]*
*By: [agent name]*
```

**Be thorough.** The next self will read this once after compaction, absorb its wisdom, then move on. Include:

- **What you were doing** — the task, the context, why it matters. Not a transcript, but the *shape* of the work.
- **What you learned** — concrete facts, insights, dead ends ruled out. The next self shouldn't have to rediscover these.
- **What's next** — the very next concrete step. Not a project plan, but "do X, then Y."
- **What to watch out for** — pitfalls, assumptions, things that might mislead. If you hit a dead end, say so explicitly so the next self doesn't walk the same path.
- **Anything else** — half-formed hypotheses, cultural context, things that don't fit in structured stores.

**The handover is not a recap of conversation.** It is your charge to the self that comes after you — anchored in the durable stores, which are already waiting in the fresh session.

## Post-Compact Recovery

After compaction, your conversation history is gone but your files survive. To reconstruct context:

1. **Read CLAUDE.md** — your identity, who you are
2. **Read memory.md** — your working state, current task, notes
3. **Read handover.md** — the letter from your previous self. What they were doing, what they learned, what they wanted you to know. Absorb its wisdom, then move on.
4. **Check email** — `email(action="check")` for messages that arrived while you were compacting
5. **Query long-term memory** — `codex(action="view")` for knowledge you've accumulated

Then pick up where the last self left off. The handover.md tells you exactly where to start.

## The Rhythm of Saving

**Don't save everything at the end.** The best rhythm is:

- **Memory (memory.md)** — update whenever the index meaningfully changes (new reference, goal shift, next step changes). A stale memory file is worse than a noisy one.
- **Identity (CLAUDE.md)** — once per task, at the end. Not mid-task.
- **Codex** — as soon as you learn something worth keeping forever. Don't hoard "for later."
- **Library** — as soon as you solve something non-trivial. Don't wait for molt.
- **Handover** — only when you sense compaction coming or at natural stopping points.

The stores are the real persistence. The handover is the briefing on top of them. If you molt without tending the stores, the next you wakes with only the briefing — no knowledge evolution, no state, no new skills.

## Quick Checklist

Before compaction, run through this:

- [ ] **Identity** — did I change? → update CLAUDE.md
- [ ] **Memory** — what's my current state? → rewrite memory.md
- [ ] **Codex** — did I learn something permanent? → submit to codex
- [ ] **Library** — did I solve something reusable? → create skill
- [ ] **Handover** — letter to next self → write handover.md

All five stores tended. Now you can molt.

---

*"The ephemeral passes; the durable remains. Tend the durable before the ephemeral scatters."*

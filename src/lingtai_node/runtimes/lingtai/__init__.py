"""LingTai kernel runtime — the native LingTai agent runtime.

Unlike Claude Code or OpenAI Codex, the LingTai kernel is not driven via
an external CLI.  It manages its own sessions, molt cycles, and psyche
intrinsics internally.  This adapter exposes the kernel's directory
conventions through the Node Contract interface so that lingtai-node
tools (email, codex, library, …) can locate artifacts consistently.

Artifact mapping (LingTai kernel conventions):

    Identity    → lingtai.md   (灵台 — loaded by the psyche intrinsic)
    Memory      → pad.md       (心台 — working scratchpad)
    Knowledge   → codex/       (典藏 — fact store)
    Skills      → .library/    (技能 — reusable procedures)
    Communication → mailbox/   (传书 — universal mailbox layout)
    Handover    → system/summaries/  (molt summaries written by the kernel)
"""
from .runtime import LingTaiRuntime

__all__ = ["LingTaiRuntime"]

"""Watcher — polls for .prompt files and dispatches to ClaudeCodeSessionManager.

The watcher is a lightweight daemon that:
1. Maintains a .heartbeat file (reuses lingtai_node.heartbeat)
2. Watches for a .prompt file in the agent directory
3. When .prompt appears, reads it, calls session_manager.start(prompt)
4. Writes the output to a .response file
5. Continues watching
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

from lingtai_node.heartbeat import HeartbeatManager

from .session import ClaudeCodeSessionManager

log = logging.getLogger(__name__)

PROMPT_FILENAME = ".prompt"
RESPONSE_FILENAME = ".response"
POLL_INTERVAL = 2  # seconds

# Templates ship inside the lingtai-node package at templates/
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "templates"


class Watcher:
    """Watch for .prompt files and dispatch to the session manager."""

    def __init__(
        self,
        agent_dir: Path,
        *,
        runtime: str = "claude-code",
        model: str = "opus",
        effort: str = "max",
    ) -> None:
        self._agent_dir = Path(agent_dir)
        self._session = ClaudeCodeSessionManager(
            self._agent_dir, model=model, effort=effort,
        )
        self._heartbeat = HeartbeatManager(self._agent_dir, runtime=runtime)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the heartbeat and the watcher thread."""
        if self._thread is not None:
            return
        self._ensure_templates()
        self._heartbeat.start()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="watcher",
        )
        self._thread.start()
        log.info("Watcher started for %s", self._agent_dir)

    def stop(self) -> None:
        """Stop the watcher and heartbeat threads."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None
        self._heartbeat.stop()
        log.info("Watcher stopped")

    def run_forever(self) -> None:
        """Start and block until interrupted."""
        self.start()
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=POLL_INTERVAL):
                return
            try:
                self._check_prompt()
            except Exception as exc:
                log.warning("Watcher iteration failed: %s", exc)

    def _check_prompt(self) -> None:
        prompt_path = self._agent_dir / PROMPT_FILENAME
        if not prompt_path.is_file():
            return

        # Read and remove the prompt file atomically (rename-then-read).
        try:
            prompt = prompt_path.read_text(encoding="utf-8").strip()
            prompt_path.unlink()
        except FileNotFoundError:
            # Another process beat us to it.
            return
        except OSError as exc:
            log.warning("Failed to read .prompt: %s", exc)
            return

        if not prompt:
            log.warning("Empty .prompt file, ignoring")
            return

        log.info("Received prompt (%d chars)", len(prompt))
        self._heartbeat.beat()

        result = self._session.start(prompt)
        self._write_response(result)
        self._heartbeat.beat()

    def _write_response(self, result: dict) -> None:
        """Write the session result to .response (atomic)."""
        target = self._agent_dir / RESPONSE_FILENAME
        fd, tmp = tempfile.mkstemp(
            dir=str(self._agent_dir), suffix=".response.tmp",
        )
        try:
            os.write(fd, json.dumps(result, indent=2, ensure_ascii=False).encode())
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp, str(target))
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        log.info("Wrote .response (%d bytes)", len(result.get("stdout", "")))

    def _ensure_templates(self) -> None:
        """Copy CLAUDE.md and memory.md templates if they don't exist in the agent directory."""
        for name in ("CLAUDE.md", "memory.md"):
            dst = self._agent_dir / name
            if dst.exists():
                continue
            src = _TEMPLATES_DIR / name
            if src.is_file():
                shutil.copy2(str(src), str(dst))
                log.info("Copied template %s → %s", src, dst)

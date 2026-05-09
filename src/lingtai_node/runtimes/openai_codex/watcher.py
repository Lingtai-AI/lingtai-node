"""Watcher — polls for .prompt files and dispatches to OpenAICodexSessionManager.

The watcher is a lightweight daemon that:
1. Maintains a .heartbeat file (reuses lingtai_node.heartbeat)
2. Watches for a .prompt file in the agent directory
3. When .prompt appears, reads it, calls session_manager.start(prompt)
4. Writes the output to a .response file
5. Continues watching
"""
from __future__ import annotations

import importlib.resources
import json
import logging
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

from lingtai_node.heartbeat import HeartbeatManager

from .session import OpenAICodexSessionManager

log = logging.getLogger(__name__)

PROMPT_FILENAME = ".prompt"
RESPONSE_FILENAME = ".response"
POLL_INTERVAL = 2  # seconds


class Watcher:
    """Watch for .prompt files and dispatch to the session manager."""

    def __init__(
        self,
        agent_dir: Path,
        *,
        model: str = "o3",
    ) -> None:
        self._agent_dir = agent_dir
        self._session_mgr = OpenAICodexSessionManager(agent_dir, model=model)
        self._heartbeat = HeartbeatManager(agent_dir, source="openai-codex-watcher")
        self._stop_event = threading.Event()
        self._ensure_templates()

    def start(self) -> None:
        """Start watching for .prompt files."""
        log.info("Starting OpenAI Codex watcher in %s", self._agent_dir)
        self._heartbeat.start()

        try:
            while not self._stop_event.is_set():
                self._poll_once()
                self._stop_event.wait(POLL_INTERVAL)
        finally:
            self._heartbeat.stop()

    def stop(self) -> None:
        """Signal the watcher to stop."""
        self._stop_event.set()

    def _poll_once(self) -> None:
        """Check for a .prompt file and process it."""
        prompt_path = self._agent_dir / PROMPT_FILENAME
        if not prompt_path.exists():
            return

        # Read and remove the prompt file atomically
        try:
            # Rename first to prevent race conditions
            tmp_path = prompt_path.with_suffix(".prompt.processing")
            os.rename(str(prompt_path), str(tmp_path))
            prompt = tmp_path.read_text(encoding="utf-8").strip()
            tmp_path.unlink()
        except OSError as e:
            log.warning("Failed to read .prompt file: %s", e)
            return

        if not prompt:
            log.warning("Empty .prompt file, ignoring")
            return

        log.info("Dispatching prompt to Codex: %s", prompt[:100])

        # Run the session manager
        result = self._session_mgr.start(prompt)

        # Write the response
        response_path = self._agent_dir / RESPONSE_FILENAME
        try:
            fd, tmp_response = tempfile.mkstemp(
                dir=str(self._agent_dir),
                prefix=".response.",
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
            os.replace(tmp_response, str(response_path))
        except OSError as e:
            log.error("Failed to write .response file: %s", e)

        log.info("Wrote .response (%d bytes)", len(result.get("stdout", "")))

    def _ensure_templates(self) -> None:
        """Copy AGENTS.md template if it doesn't exist in the agent directory."""
        for name in ("AGENTS.md",):
            dst = self._agent_dir / name
            if dst.exists():
                continue
            
            # Use importlib.resources to load templates from the package
            try:
                template_ref = importlib.resources.files("lingtai_node.templates").joinpath(name)
                with importlib.resources.as_file(template_ref) as template_path:
                    shutil.copy2(str(template_path), str(dst))
                    log.info("Copied template %s → %s", template_path, dst)
            except (FileNotFoundError, TypeError) as e:
                log.warning("Template %s not found in package: %s", name, e)

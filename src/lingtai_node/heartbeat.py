"""Heartbeat manager — proves agent liveness via .heartbeat file.

Maintains {agent_dir}/.heartbeat with a JSON payload containing the
last-updated timestamp, runtime type, and status. Updated on every tool
call and by a background daemon thread every 15 seconds if idle.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

HEARTBEAT_FILENAME = ".heartbeat"
HEARTBEAT_INTERVAL = 15  # seconds


class HeartbeatManager:
    """Writes and refreshes the .heartbeat file."""

    def __init__(self, agent_dir: Path, runtime: str = "claude-code") -> None:
        self._agent_dir = Path(agent_dir)
        self._runtime = runtime
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def heartbeat_path(self) -> Path:
        return self._agent_dir / HEARTBEAT_FILENAME

    def _payload(self) -> dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "runtime": self._runtime,
            "status": "alive",
            "pid": os.getpid(),
        }

    def beat(self) -> None:
        """Write the heartbeat file (atomic)."""
        self._agent_dir.mkdir(parents=True, exist_ok=True)
        payload = self._payload()
        target = self.heartbeat_path
        fd, tmp = tempfile.mkstemp(
            dir=str(self._agent_dir), suffix=".heartbeat.tmp",
        )
        try:
            os.write(fd, json.dumps(payload, indent=2).encode())
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

    def start(self) -> None:
        """Start the background heartbeat thread."""
        if self._thread is not None:
            return
        self.beat()  # immediate first beat
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="heartbeat",
        )
        self._thread.start()
        log.info("Heartbeat thread started (interval=%ds)", HEARTBEAT_INTERVAL)

    def stop(self) -> None:
        """Signal the heartbeat thread to stop."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=HEARTBEAT_INTERVAL):
                return
            try:
                self.beat()
            except Exception as e:
                log.warning("Heartbeat write failed: %s", e)

    def read(self) -> dict | None:
        """Read the current heartbeat file. Returns None if missing."""
        path = self.heartbeat_path
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

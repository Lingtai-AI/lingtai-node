#!/usr/bin/env python3
"""Entry point for the LingTai Node watcher daemon.

Usage:
    python -m scripts.watch /path/to/agent_dir
    # or
    python scripts/watch.py /path/to/agent_dir
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch an agent directory for .prompt files and dispatch to Claude Code",
    )
    parser.add_argument(
        "agent_dir",
        type=Path,
        help="Path to the agent directory to watch",
    )
    parser.add_argument(
        "--runtime",
        default="claude-code",
        help="Runtime identifier for heartbeat (default: claude-code)",
    )
    parser.add_argument(
        "--model",
        default="opus",
        help="Claude model to use (default: opus)",
    )
    parser.add_argument(
        "--effort",
        default="max",
        help="Claude effort level (default: max)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    agent_dir = args.agent_dir.resolve()
    if not agent_dir.is_dir():
        print(f"Error: {agent_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    from lingtai_node.runtimes.claude_code import Watcher

    watcher = Watcher(
        agent_dir,
        runtime=args.runtime,
        model=args.model,
        effort=args.effort,
    )
    watcher.run_forever()


if __name__ == "__main__":
    main()

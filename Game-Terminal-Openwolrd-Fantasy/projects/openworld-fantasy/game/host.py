"""
W3 world host process — file-mode heartbeat + index refresh.

Usage:
  python -m game.host default
  python -m game.host default --interval 5
  python -m game.host status default

Does not replace the game client. Run in a second terminal while playing
to keep world_meta host alive and player index fresh.
"""
from __future__ import annotations

import argparse
import signal
import sys
import time
from typing import Optional


def run_host(world_id: str, *, interval: float = 5.0) -> int:
    from game.config import APP_VERSION
    from game.domain.world_meta import (
        format_host_status_lines,
        host_heartbeat,
        refresh_world_index,
    )
    from game.domain.world_social import build_world_ranking, write_rank_board_soft

    stop = {"flag": False}

    def _stop(*_a):
        stop["flag"] = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    print(f"[host] Open World Fantasy {APP_VERSION} · world={world_id}")
    print(f"[host] interval={interval}s · Ctrl+C to stop")
    print("[host] mode=file (locks under saves/{world}/.locks/)")

    # initial refresh
    try:
        from game.data_load.registry import get_registry

        refresh_world_index(world_id)
        reg = get_registry()
        board = build_world_ranking(world_id, reg)
        write_rank_board_soft(world_id, board)
    except Exception as exc:
        print(f"[host] warmup warn: {exc}")

    n = 0
    while not stop["flag"]:
        n += 1
        try:
            host_heartbeat(world_id)
            if n % 3 == 0:
                refresh_world_index(world_id)
            if n % 6 == 0:
                from game.data_load.registry import get_registry

                reg = get_registry()
                board = build_world_ranking(world_id, reg)
                write_rank_board_soft(world_id, board)
            if n % 2 == 0:
                print(f"[host] beat #{n} · {time.strftime('%H:%M:%S')}")
        except Exception as exc:
            print(f"[host] error: {exc}")
        # sleep in slices so Ctrl+C is snappy
        end = time.time() + max(1.0, float(interval))
        while time.time() < end and not stop["flag"]:
            time.sleep(0.2)

    print("[host] stopped")
    for line in format_host_status_lines(world_id):
        print(line)
    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Open World Fantasy · W3 world host")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        help="run | status",
    )
    parser.add_argument("world_id", nargs="?", default="default", help="world id")
    parser.add_argument("--interval", type=float, default=5.0, help="heartbeat seconds")
    args = parser.parse_args(argv)

    # allow: python -m game.host default  OR  python -m game.host run default
    cmd = args.command
    wid = args.world_id
    if cmd not in ("run", "status") and args.world_id == "default":
        # treat first positional as world_id
        wid = cmd
        cmd = "run"
    elif cmd not in ("run", "status"):
        wid = cmd
        cmd = "run"

    if cmd == "status":
        from game.domain.world_meta import format_host_status_lines

        for line in format_host_status_lines(wid):
            print(line)
        return 0

    return run_host(wid, interval=args.interval)


if __name__ == "__main__":
    sys.exit(main())

"""Shared field helpers."""
from __future__ import annotations
from typing import List, Optional
from game.ports.io import IO


def _emit_personality_notes(io: IO, notes: Optional[List[str]]) -> None:
    if not notes:
        return
    for n in notes:
        if n:
            io.write_line(n)

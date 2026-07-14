"""Game-test helpers (ScriptedIO sessions, save isolation)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from game.ports.io import ScriptedIO
from game.services.field_loop import interactive_create, run_field


def isolated_saves(monkeypatch, tmp_path: Path) -> Path:
    """Redirect save/export dirs so smoke tests never touch real saves/."""
    monkeypatch.setattr("game.services.save_service.SAVES_DIR", tmp_path / "saves")
    monkeypatch.setattr("game.services.save_service.EXPORT_DIR", tmp_path / "exports")
    (tmp_path / "saves").mkdir(parents=True, exist_ok=True)
    (tmp_path / "exports").mkdir(parents=True, exist_ok=True)
    return tmp_path


def create_script(
    name: str = "SmokeHero",
    gender: str = "1",  # 1=ชาย 2=หญิง
    birth: str = "15/6/2000",
    occupation_index: str = "1",  # ignored — start as vagabond (no class pick)
) -> List[str]:
    """Inputs for ``interactive_create`` (name, gender 1|2, birth, Enter)."""
    return [name, gender, birth, ""]


def field_exit_script(
    *actions: str,
    include_tutorial: bool = False,
) -> List[str]:
    """Build a field-loop script that ends with ``0`` (auto-save exit).

    Tutorial is 8 Enter pages when ``include_tutorial`` is True (1.38+).
    """
    lines: List[str] = []
    if include_tutorial:
        lines.extend(["", "", "", "", "", "", "", ""])  # 8 tutorial pages
    lines.extend(actions)
    if not lines or lines[-1] != "0":
        lines.append("0")
    return lines


def run_create_session(reg, inputs: Sequence[str]):
    io = ScriptedIO(list(inputs))
    player = interactive_create(reg, io)
    return player, io


def run_field_session(
    player: Dict[str, Any],
    reg,
    inputs: Sequence[str],
    *,
    raise_on_empty: bool = True,
    seed: Optional[int] = None,
    rng=None,
) -> ScriptedIO:
    io = ScriptedIO(list(inputs), raise_on_empty=raise_on_empty)
    try:
        run_field(player, reg, io, rng=rng, seed=seed)
    except EOFError:
        # expected when script ends without explicit exit
        pass
    return io

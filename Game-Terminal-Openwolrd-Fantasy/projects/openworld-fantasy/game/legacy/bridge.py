"""Load and adapt the playable prototype (P0 bridge).

Later phases replace this with modular domain services.
"""
from __future__ import annotations

import importlib.util
import sys
from types import ModuleType
from typing import Any, Callable

from game.config import PROTOTYPE_PATH
from game.ui_terminal.status import render_status_l1


def load_prototype_module() -> ModuleType:
    path = PROTOTYPE_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Prototype not found: {path}")

    name = "pixel_fantasy_openskill_runtime"
    # Reuse if already loaded
    if name in sys.modules:
        return sys.modules[name]

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load prototype: {path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def install_l1_status(mod: ModuleType) -> None:
    """Replace prototype show_status with L1 boxed UI."""

    def show_status(player: Any, current_area: str) -> None:
        print()
        print(render_status_l1(player, current_area))

    mod.show_status = show_status  # type: ignore[attr-defined]


def run_prototype_game() -> None:
    mod = load_prototype_module()
    install_l1_status(mod)
    main_game: Callable[[], None] = mod.main_game
    main_game()

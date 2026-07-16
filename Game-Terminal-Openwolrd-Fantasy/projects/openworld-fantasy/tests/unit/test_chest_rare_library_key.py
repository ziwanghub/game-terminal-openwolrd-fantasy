"""Regression: rare_relic chest + grant_library_key (UnboundLocalError fix)."""
from __future__ import annotations

import random
from unittest.mock import patch

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.ports.io import ScriptedIO
from game.services.field_encounters import _handle_sight


def test_rare_relic_chest_can_grant_library_key():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ChestLib", "warrior", "ตุลย์")
    sight = {"kind": "chest", "label": "หีบเก่า", "hint": "สลักเลือน", "id": "ch01"}
    io = ScriptedIO([])

    class R(random.Random):
        def random(self):
            return 0.1  # < 0.4 → grant key

        def randint(self, a, b):
            return 100

    with patch(
        "game.services.field_encounters.resolve_approach", return_value="rare_relic"
    ):
        _handle_sight(p, reg, io, R(0), sight)
    out = io.joined()
    assert "referenced before assignment" not in out.lower()
    assert "UnboundLocalError" not in out
    assert "เงินโลก" in out or "หายาก" in out or "โชคดี" in out

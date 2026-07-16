"""WO-017 R3: one care/fight action = one auto_run counter."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import recompute_stats
from game.domain.needs import ensure_needs
from game.runtime.auto_run_log import (
    bump_auto_run,
    ensure_auto_run,
    observe_auto_lines,
    start_auto_run,
)
from game.runtime.dungeon_auto import ensure_auto_prefs, run_auto_needs_care


def test_observe_does_not_double_count_without_count_flag():
    p = create_player(DataRegistry.load(DATA_DIR), "c1", "warrior", "ตุลย์")
    start_auto_run(p, kind="field", label="t", max_ticks=10)
    lines = [
        "  ออโต้: พักเพราะล้า (ล้า 74 ≥ 62)",
        "  …พักครู่ — ลมหายใจยาวขึ้น",
        "  ออโต้: พักครบติก — ไม่สำรวจต่อในจังหวะนี้",
        "ออโต้ชนะ Wolf · XP +3",
        "ออโต้ชนะ Wolf · XP +3",
    ]
    observe_auto_lines(p, lines)  # default count=False
    sess = ensure_auto_run(p)
    assert int(sess.get("rests") or 0) == 0
    assert int(sess.get("fights") or 0) == 0
    # with count=True still once per kind per batch
    observe_auto_lines(p, lines, count=True)
    sess = ensure_auto_run(p)
    assert int(sess.get("rests") or 0) == 1
    assert int(sess.get("fights") or 0) == 1


def test_care_bumps_once_per_eat_or_rest():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "c2", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    ensure_auto_prefs(p)
    start_auto_run(p, kind="field", label="t", max_ticks=5)
    p["needs"] = {"hunger": 80, "fatigue": 80, "morale": 50}
    p["auto_prefs"]["hunger"] = 50
    p["auto_prefs"]["fatigue"] = 50
    # give food
    p["inventory_ids"] = list(p.get("inventory_ids") or [])
    for iid, it in (reg.items or {}).items():
        if (it or {}).get("food_tier"):
            p["inventory_ids"].append(iid)
            break
    lines, stop, avoid, rested = run_auto_needs_care(p, reg, allow_rest=True)
    sess = ensure_auto_run(p)
    # at most one eat and/or one rest this pass
    assert int(sess.get("eats") or 0) <= 1
    assert int(sess.get("rests") or 0) <= 1
    if rested:
        assert int(sess.get("rests") or 0) == 1

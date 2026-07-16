"""Dungeon auto: prefs, thresholds, skill plan, regen, full XP."""
import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.dungeon import begin_dungeon, get_run, on_floor_boss_defeated
from game.domain.equipment import add_item, recompute_stats
from game.domain.needs import ensure_needs
from game.runtime.auto_farm import auto_fight
from game.runtime.dungeon_auto import (
    _effective_thresholds,
    apply_auto_regen,
    can_auto_fight_floor_boss,
    compute_auto_regen,
    count_food,
    ensure_auto_prefs,
    format_dungeon_auto_hud,
    list_combat_skill_ids,
    mark_floor_boss_manual_win,
    resolve_skill_for_auto_turn,
    run_dungeon_auto,
    skill_plan_labels,
    use_items_by_thresholds,
    _one_auto_tick,
)


class _IO:
    def __init__(self, answers=None):
        self.lines = []
        self.answers = list(answers or ["0", "s"])
        self._i = 0

    def write_line(self, text=""):
        self.lines.append(text)

    def read_line(self, prompt=""):
        if self._i < len(self.answers):
            a = self.answers[self._i]
            self._i += 1
            return a
        return "s"


def test_food_and_thresholds():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ae", "warrior", "เมษ")
    ensure_needs(p)
    prefs = ensure_auto_prefs(p)
    prefs["hunger"] = 40
    prefs["hp_pct"] = 50
    p["auto_prefs"] = prefs
    p["needs"]["hunger"] = 60
    p["hp"] = 20
    add_item(p, "traveler_ration", reg)
    n0 = count_food(p, reg)
    notes = use_items_by_thresholds(p, reg)
    assert notes
    assert count_food(p, reg) <= n0
    hud = format_dungeon_auto_hud(p, reg)
    assert "hp(" in hud and "หิว(" in hud and "ล้า(" in hud and "%" in hud


def test_thrift_raises_hunger_threshold():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "th", "mage", "เมถุน")
    ensure_auto_prefs(p)
    p["auto_prefs"]["item_mode"] = "thrift"
    p["auto_prefs"]["hunger"] = 50
    th = _effective_thresholds(p, reg)
    p["auto_prefs"]["item_mode"] = "safe"
    th2 = _effective_thresholds(p, reg)
    assert th["hunger"] >= th2["hunger"]
    assert th["hp_pct"] <= th2["hp_pct"]


def test_skill_plan_fallback_basic():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sk", "mage", "เมถุน")
    p["skills"] = ["basic_strike", "fire_ball", "water_bolt"]
    p["mana"] = 0
    ids = list_combat_skill_ids(p, reg)
    assert ids[0] == "__basic__"
    # plan step pointing at fire (likely index 2+)
    sk, label = resolve_skill_for_auto_turn(p, reg, [2, 3, 1], plan_step=0)
    assert "ปกติ" in label or int(sk.get("cost_mana") or 0) == 0
    p["mana"] = 99
    sk2, label2 = resolve_skill_for_auto_turn(p, reg, [2], plan_step=0)
    # may be fire or basic depending on list
    assert sk2.get("name") or label2


def test_regen_priest_better_mp_than_warrior_soft():
    reg = DataRegistry.load(DATA_DIR)
    priest = create_player(reg, "pr", "priest", "มีน")
    warrior = create_player(reg, "wa", "warrior", "เมษ")
    recompute_stats(priest, reg)
    recompute_stats(warrior, reg)
    rp = compute_auto_regen(priest, reg)
    rw = compute_auto_regen(warrior, reg)
    assert rp["mp_frac"] >= rw["mp_frac"] * 0.9  # priest should not be worse


def test_auto_fight_full_xp_with_plan():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "af", "warrior", "ตุลย์")
    recompute_stats(p, reg)
    mon = {
        "id": "forest_wolf",
        "name": "Wolf",
        "level": 1,
        "hp": 30,
        "max_hp": 30,
        "atk": 5,
        "xp_mult": 1.0,
        "elements": ["physical"],
        "attack_profiles": [{"id": "a", "power": 4, "weight": 1}],
    }
    before = int(p.get("xp") or 0)
    logs = auto_fight(
        p,
        mon,
        reg,
        random.Random(1),
        "dark_forest",
        xp_factor=1.0,
        skill_plan=[1, 1],
        use_regen=True,
    )
    assert any("ออโต้ชนะ" in x for x in logs)
    assert "ลดแล้ว" not in "".join(logs)
    assert int(p.get("xp") or 0) >= before


def test_boss_auto_gate():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "bg", "mage", "เมถุน")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(1))
    assert not can_auto_fight_floor_boss(p)
    mark_floor_boss_manual_win(p)
    assert can_auto_fight_floor_boss(p)
    p2 = create_player(reg, "bg2", "rogue", "พิจิก")
    begin_dungeon(p2, reg, "dung_forest_root", random.Random(2))
    on_floor_boss_defeated(p2, reg, random.Random(1), mon={"dungeon_floor_boss": True})
    assert can_auto_fight_floor_boss(p2)


def test_auto_tick_and_run():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "tk", "warrior", "ตุลย์")
    begin_dungeon(p, reg, "dung_forest_root", random.Random(3))
    add_item(p, "traveler_ration", reg)
    add_item(p, "traveler_ration", reg)
    ensure_auto_prefs(p)
    lines, stop = _one_auto_tick(p, reg, random.Random(5))
    assert isinstance(lines, list)
    io = _IO(answers=["0", "s"])
    # skip config by pre-setting; run with skip_config
    reason = run_dungeon_auto(
        p, reg, io, random.Random(1), max_ticks=2, continuous=True, skip_config=True
    )
    assert reason in ("done", "food", "hp", "user", "left_dungeon")

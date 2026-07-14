"""
Automated mini playtest loop — smoke critical solo systems end-to-end.
Not a full fun playtest; catches wiring regressions.
"""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.class_paths import (
    apply_class_change,
    decline_class_offer,
    list_available_class_paths,
)
from game.domain.equipment import add_item, equip_item, recompute_stats, upgrade_cost
from game.domain.inventory_sys import upgrade_equipped_opaque
from game.domain.progression import allocate_stat, on_level_up_points
from game.domain.skill_tree import learn_skill
from game.domain.unit_system import (
    apply_unit_skill_scaling,
    try_unit_unlock_with_claim,
)


def test_solo_smoke_occupation_gear_upgrade_tree():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "Smoke", "vagabond", "เมษ")
    p["id"] = "smoke_hero_001"
    p["world_id"] = "_smoke_world"
    p["level"] = 12
    p["money_world"] = 5000
    p["stats_alloc"] = {
        "atk": 6,
        "defense": 5,
        "magic": 4,
        "speed": 4,
        "intelligence": 3,
        "crit": 2,
    }
    p["stats"] = {
        "kills": 30,
        "combos": 25,
        "explores": 20,
        "flees": 3,
        "heals": 5,
        "boss_kills": 1,
    }
    p["library_entries_read"] = ["a", "b"]
    p["personality_invest"] = {"compassion": 2}
    p["stat_points"] = 3

    # class offer path
    paths = list_available_class_paths(p, reg)
    assert paths
    # decline one if multiple, accept warrior-ish or first remaining
    if len(paths) > 1:
        decline_class_offer(p, paths[0])
        paths = list_available_class_paths(p, reg)
    path = next(
        (x for x in paths if x.get("to_occupation") == "warrior"),
        paths[0],
    )
    notes = apply_class_change(p, reg, path)
    assert p.get("occupation_id") == path.get("to_occupation")
    assert any("รับ" in n or "→" in n for n in notes)

    # gear
    add_item(p, "iron_sword", reg, rarity="uncommon")
    add_item(p, "leather_armor", reg, rarity="common")
    msg = equip_item(p, "iron_sword", reg)
    assert "สวม" in msg
    equip_item(p, "leather_armor", reg)
    recompute_stats(p, reg)
    assert int(p.get("equip_def") or 0) >= 1
    assert int(p.get("bonus_atk") or 0) > int(p.get("base_atk") or 0)

    # upgrade once (forced success)
    for _ in range(10):
        add_item(p, "upgrade_mat", reg)

    class Ok:
        def random(self):
            return 0.0

    up_msg = upgrade_equipped_opaque(p, "main_hand", reg, rng=Ok())  # type: ignore
    assert "สำเร็จ" in up_msg or "ไม่พอ" in up_msg

    # allocate soft
    msg_a = allocate_stat(p, reg, "atk", 1)
    assert "เพิ่ม" in msg_a

    # skill tree learn if root present
    occ = str(p.get("occupation_id") or "")
    roots = {
        "warrior": "warrior_cleave",
        "mage": "mage_ember",
        "archer": "archer_aimed",
        "rogue": "rogue_poison_edge",
        "priest": "priest_smite",
    }
    root = roots.get(occ)
    if root and root in reg.skills:
        p["level"] = max(int(p.get("level") or 1), 10)
        p["money_world"] = max(int(p.get("money_world") or 0), 500)
        # ensure prereq skill
        base_sk = (reg.occupations.get(occ) or {}).get("skill")
        if base_sk and base_sk not in (p.get("skills") or []):
            p.setdefault("skills", []).append(base_sk)
        learn_msg = learn_skill(p, reg, root, free=True)
        assert "เรียน" in learn_msg or "มีสกิล" in learn_msg

    # cost curve sanity
    assert upgrade_cost("main_hand", 5)["money"] < upgrade_cost("main_hand", 9)["money"]


def test_solo_smoke_unit_hsr_force():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "USmoke", "mage", "เมถุน")
    p["id"] = "smoke_unit_001"
    p["world_id"] = "_smoke_unit_world"
    p["level"] = 30
    p["stats_alloc"] = {
        "atk": 2,
        "defense": 2,
        "magic": 18,
        "speed": 4,
        "intelligence": 10,
        "crit": 2,
    }
    p["stats"] = {"boss_kills": 5, "kills": 50, "combos": 40}
    p["library_entries_read"] = list("abcdefgh")
    p["location"] = "void_rift"
    p["power_mag"] = 40
    p["power_atk"] = 10

    from game.domain.unit_system import save_claims

    save_claims("_smoke_unit_world", {"by_unit": {}, "by_skill": {}, "schema": 2})
    notes = try_unit_unlock_with_claim(
        p, reg, force_uid="unit_nova", force_success=True
    )
    assert p.get("unit_class_id") == "unit_nova"
    assert any("อาชีพลับ" in n or "Unit" in n or "ปลุก" in n for n in notes)

    sk = reg.skills[p["unit_skill"]]
    dmg, mana = apply_unit_skill_scaling(
        p, sk, int(sk.get("power") or 50), int(sk.get("cost_mana") or 20), reg=reg
    )
    assert dmg >= 1
    assert mana >= 0

    # second unit blocked
    notes2 = try_unit_unlock_with_claim(
        p, reg, force_uid="unit_eclipse", force_success=True
    )
    assert notes2 == []
    assert p.get("unit_class_id") == "unit_nova"


def test_solo_smoke_level_up_bundle():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "LvSmoke", "vagabond", "เมษ")
    p["level"] = 5
    notes = on_level_up_points(p, reg, 1)
    assert notes
    assert int(p.get("stat_points") or 0) >= 1


def test_solo_smoke_combo_mind_and_skill_rank():
    """Post-CM/SK-R wiring: P refuse int · combo steps · rank scale · soft mana msg."""
    from game.domain.combo import max_combo_for_player, resolve_combo
    from game.domain.combo_mind import (
        ensure_focus_latent,
        soft_combo_mana_fail_message,
        soft_combo_mind_hint,
    )
    from game.domain.progression import ALLOCATE_KEYS, init_progression
    from game.domain.skill_rank import scale_skill_for_player, set_skill_rank
    from game.ui_terminal.status import render_status_l1

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "CMSmoke", "mage", "เมษ")
    init_progression(p, reg)
    p["level"] = 12
    p["location"] = "dark_forest"
    p["stat_points"] = 5
    p["skills"] = ["water_bolt", "wind_slash", "fire_ball", "magic_missile"]
    p["mana"] = 5
    p["max_mana"] = 80

    # CM3: no free int
    assert "intelligence" not in ALLOCATE_KEYS
    refuse = allocate_stat(p, reg, "intelligence", 2)
    assert "ไม่ได้" in refuse or "แจก" in refuse
    assert int(p.get("stat_points") or 0) == 5

    ensure_focus_latent(p, reg)
    n = max_combo_for_player(p, reg)
    assert 2 <= n <= 6
    hint = soft_combo_mind_hint(p, reg)
    assert "จิต" in hint or "ฉลาด" in hint

    set_skill_rank(p, "fire_ball", "S", reg)
    sk = scale_skill_for_player(p, reg.skills["fire_ball"], reg, skill_id="fire_ball")
    assert int(sk.get("power") or 0) >= int(reg.skills["fire_ball"].get("power") or 0)

    combo = resolve_combo(["water_bolt", "wind_slash"], reg, max_n=n, player=p)
    assert combo.get("ok")
    assert int(combo.get("total_mana") or 0) >= 1
    fail = soft_combo_mana_fail_message(
        p, int(combo["total_mana"]), int(p["mana"]), reg, length=2
    )
    assert "มานา" in fail or "โซ่" in fail or str(combo["total_mana"]) in fail

    status_txt = render_status_l1(p, "dark_forest")
    assert "ลงทุน" in status_txt or "เวท" in status_txt
    assert "จิต" in status_txt or "ฉลาด" in status_txt

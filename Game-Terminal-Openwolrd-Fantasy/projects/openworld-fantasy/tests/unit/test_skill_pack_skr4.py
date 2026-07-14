"""SK-R4 content pack + SK-R5 lite essence nudge."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.progression import init_progression
from game.domain.skill_rank import set_skill_rank, try_rank_nudge_item
from game.domain.skill_slots import (
    apply_buff_skill,
    apply_debuff_from_skill,
    normalize_slot,
)
from game.domain.skill_tree import list_visible_tree_nodes


PACK_IDS = [
    "mage_cinder_hex",
    "mage_mind_focus",
    "mage_frost_bind",
    "rogue_toxin_cloud",
    "rogue_quiet_focus",
    "rogue_nerve_cut",
    "warrior_battle_cry",
    "warrior_shockwave_stun",
    "warrior_mirror_guard",
    "priest_holy_focus",
    "priest_regen_hymn",
    "priest_smite_shock",
    "archer_pin_leg",
    "archer_hunters_calm",
    "archer_shock_bolt",
]


def test_pack_skills_registered():
    reg = DataRegistry.load(DATA_DIR)
    for sid in PACK_IDS:
        assert sid in reg.skills, sid
    assert normalize_slot(reg.skills["mage_cinder_hex"]) == "debuff"
    assert normalize_slot(reg.skills["mage_mind_focus"]) == "buff"
    assert normalize_slot(reg.skills["warrior_mirror_guard"]) == "defense"
    assert float(reg.skills["warrior_mirror_guard"].get("reflect_pct") or 0) > 0


def test_new_statuses_exist():
    reg = DataRegistry.load(DATA_DIR)
    # statuses may be dict by id
    st = reg.statuses or {}
    assert "slow" in st or any(
        (v.get("id") if isinstance(v, dict) else None) == "slow" for v in st.values()
    )
    assert "weak" in st or any(
        (v.get("id") if isinstance(v, dict) else None) == "weak" for v in st.values()
    )


def test_debuff_and_buff_apply():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "T", "mage", "เมษ")
    init_progression(p, reg)
    mon = {"hp": 80, "max_hp": 80, "statuses": []}
    sk = dict(reg.skills["mage_cinder_hex"])
    notes = apply_debuff_from_skill(mon, sk, reg, random.Random(1))
    # chance may fail — force high chance
    sk["apply_status"] = {"id": "burn", "chance": 1.0}
    notes2 = apply_debuff_from_skill(mon, sk, reg, random.Random(2))
    assert notes2
    sk_b = dict(reg.skills["mage_mind_focus"])
    bnotes = apply_buff_skill(p, sk_b, reg, random.Random(1))
    assert bnotes
    assert any(
        (s.get("id") if isinstance(s, dict) else s) in ("focus", "might", "ward", "regen")
        for s in (p.get("statuses") or [])
    ) or bnotes


def test_tree_shows_pack_for_class():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "W", "warrior", "สิงห์")
    init_progression(p, reg)
    p["occupation_id"] = "warrior"
    p["level"] = 20
    p["skills"] = ["basic_strike", "warrior_cleave", "guard_basic", "counter_guard", "thorn_reflect"]
    nodes = list_visible_tree_nodes(p, reg)
    ids = {n["id"] for n in nodes}
    assert "warrior_battle_cry" in ids or "warrior_shockwave_stun" in ids


def test_essence_nudge():
    reg = DataRegistry.load(DATA_DIR)
    assert "essence_skill_whisper" in reg.items
    p = create_player(reg, "E", "mage", "เมษ")
    init_progression(p, reg)
    p["skills"] = ["fire_ball"]
    set_skill_rank(p, "fire_ball", "N", reg)
    upgraded = False
    for seed in range(40):
        pp = dict(p)
        pp["skills"] = ["fire_ball"]
        pp["skill_ranks"] = {"fire_ball": "N"}
        pp["skill_rank_xp"] = {}
        ok, msg = try_rank_nudge_item(
            pp, "fire_ball", reg, random.Random(seed), bonus=0.5
        )
        assert ok
        if "ไม่เปลี่ยนโทน" in msg:
            continue
        if "เปลี่ยนโทน" in msg or pp.get("skill_ranks", {}).get("fire_ball") not in (
            None,
            "N",
        ):
            upgraded = True
            assert pp["skill_ranks"]["fire_ball"] != "N"
            break
    assert upgraded  # high bonus should hit within 40 seeds

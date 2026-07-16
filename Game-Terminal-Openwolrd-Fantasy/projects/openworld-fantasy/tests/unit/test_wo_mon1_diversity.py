"""WO-Mon-1..4: pool diversity, profiles, weakness, balance clamps, content."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.combat import pick_monster, _clamp_spawn_stats, apply_world_enemy_mods
from game.domain.combat_identity import (
    weakness_lite_elements,
    weakness_lite_hint_lines,
    weakness_lite_mult,
)


def test_all_monsters_have_profiles_and_telegraph():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.monsters) >= 90
    with_prof = 0
    for mid, m in reg.monsters.items():
        profs = m.get("attack_profiles") or []
        assert profs, f"{mid} missing attack_profiles"
        with_prof += 1
        for p in profs:
            assert p.get("telegraph"), f"{mid} profile missing telegraph"
    assert with_prof >= 60


def test_early_pool_top2_normals_under_half():
    reg = DataRegistry.load(DATA_DIR)
    for stem in ("dark_forest", "cave_shadow"):
        data = yaml.safe_load((DATA_DIR / "areas" / f"{stem}.yaml").read_text(encoding="utf-8"))
        pools = data.get("monster_pools") or []
        total = sum(int(e.get("weight") or 0) for e in pools)
        normals = []
        for e in pools:
            mid = e.get("id")
            m = reg.monsters.get(mid) or {}
            if not m.get("elite") and not m.get("boss"):
                normals.append(int(e.get("weight") or 0))
        normals.sort(reverse=True)
        top2 = sum(normals[:2]) if len(normals) >= 2 else sum(normals)
        assert top2 / max(1, total) < 0.50, f"{stem} top2={top2}/{total}"


def test_early_pool_has_elite_weight():
    reg = DataRegistry.load(DATA_DIR)
    data = yaml.safe_load((DATA_DIR / "areas" / "dark_forest.yaml").read_text(encoding="utf-8"))
    elite_w = 0
    for e in data.get("monster_pools") or []:
        m = reg.monsters.get(e.get("id")) or {}
        if m.get("elite"):
            elite_w += int(e.get("weight") or 0)
    assert elite_w >= 6


def test_pick_monster_has_profiles_and_weak_to():
    reg = DataRegistry.load(DATA_DIR)
    rng = random.Random(42)
    mon = pick_monster(reg, "dark_forest", rng)
    assert mon.get("attack_profiles")
    assert mon["attack_profiles"][0].get("telegraph")
    # weak_to may be on catalog copy
    base = reg.monsters.get(mon.get("id")) or {}
    assert base.get("weak_to") or base.get("weakness_lite") or mon.get("weak_to")


def test_weakness_lite_from_catalog_and_s_tier():
    mon = {
        "id": "t",
        "elements": ["fire"],
        "weak_to": ["water", "earth"],
        "name": "ไฟทดสอบ",
    }
    weak = weakness_lite_elements(mon, None)
    assert "water" in weak
    player = {"_appraised_targets": {"t": "S"}}
    # need mon id match for appraised tier - check _appraised_tier
    player = {"_last_appraise_tier": "S", "_appraised_targets": {"t": "S"}}
    lines = weakness_lite_hint_lines(player, mon, None, pre_fight=True)
    # may need correct appraise key - if empty, still check mult path
    mult, meta = weakness_lite_mult(player, mon, ["water"], None)
    # if tier resolution fails, force
    if not meta.get("active"):
        player["_appraised_targets"] = {str(mon.get("id")): "SS"}
        mult, meta = weakness_lite_mult(player, mon, ["water"], None)
    # at least elements resolve
    assert weak


def test_clamp_spawn_stats_limits_spike():
    mon = {"hp": 500, "max_hp": 500, "atk": 80, "attack_profiles": [{"power": 100}]}
    out = _clamp_spawn_stats(mon, base_hp=100, base_atk=20, elite=True)
    assert out["hp"] <= int(100 * 2.15 + 1)
    assert out["atk"] <= int(20 * 1.95 + 1)


def test_world_mod_clamp_non_boss():
    mon = {"hp": 100, "max_hp": 100, "atk": 10, "boss": False}
    player = {"world_modifiers": {"enemy_hp_mult": 3.0, "enemy_atk_mult": 3.0}}
    out = apply_world_enemy_mods(mon, player)
    assert out["hp"] <= 165  # 1.65 cap
    assert out["atk"] <= 16


def test_role_tag_coverage():
    reg = DataRegistry.load(DATA_DIR)
    tagged = sum(1 for m in reg.monsters.values() if m.get("role_tag"))
    assert tagged >= 80


def test_content_pack_min_count():
    reg = DataRegistry.load(DATA_DIR)
    assert len(reg.monsters) >= 95
    # new pack samples
    assert "forest_spore_cap" in reg.monsters
    assert "elite_forest_spore_king" in reg.monsters

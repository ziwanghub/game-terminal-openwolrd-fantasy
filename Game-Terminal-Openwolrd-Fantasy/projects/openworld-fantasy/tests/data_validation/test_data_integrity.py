"""Data integrity — catch broken YAML refs before runtime."""
from __future__ import annotations

from typing import Any, Dict, List, Set

import pytest

from game.data_load.registry import DataRegistry


def _stock_item_ids(shop: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    for entry in shop.get("stock") or []:
        if isinstance(entry, str):
            ids.append(entry)
        elif isinstance(entry, dict):
            iid = entry.get("id")
            if iid:
                ids.append(str(iid))
    return ids


def test_registry_core_non_empty(reg: DataRegistry):
    assert len(reg.areas) >= 3
    assert len(reg.monsters) >= 5
    assert len(reg.skills) >= 10
    assert len(reg.occupations) >= 5
    assert len(reg.items) >= 5
    assert len(reg.worlds) >= 1


def test_area_monster_pool_refs(reg: DataRegistry):
    missing: List[str] = []
    for aid, area in reg.areas.items():
        for entry in area.get("monster_pools") or []:
            mid = entry.get("id") if isinstance(entry, dict) else entry
            if mid and mid not in reg.monsters:
                missing.append(f"{aid}.monster_pools → {mid}")
    assert not missing, "broken monster pool refs:\n" + "\n".join(missing)


def test_area_boss_refs(reg: DataRegistry):
    missing: List[str] = []
    for aid, area in reg.areas.items():
        bid = area.get("boss_id")
        if bid and bid not in reg.monsters:
            missing.append(f"{aid}.boss_id → {bid}")
    assert not missing, "broken boss refs:\n" + "\n".join(missing)


def test_area_connections_exist(reg: DataRegistry):
    missing: List[str] = []
    for aid, area in reg.areas.items():
        for dest in area.get("connections") or []:
            if dest not in reg.areas:
                missing.append(f"{aid} → {dest}")
    assert not missing, "broken area connections:\n" + "\n".join(missing)


def test_world_starting_areas(reg: DataRegistry):
    for wid, world in reg.worlds.items():
        start = world.get("starting_area")
        if start:
            assert start in reg.areas, f"world {wid} starting_area {start} missing"


def test_occupation_starter_skills(reg: DataRegistry):
    missing: List[str] = []
    for oid, occ in reg.occupations.items():
        sid = occ.get("skill")
        if sid and sid not in reg.skills:
            missing.append(f"{oid}.skill → {sid}")
    assert not missing, "broken occupation skills:\n" + "\n".join(missing)


def test_shop_stock_item_refs(reg: DataRegistry):
    missing: List[str] = []
    for sid, shop in reg.shops.items():
        for iid in _stock_item_ids(shop):
            if iid not in reg.items and iid not in reg.cards:
                missing.append(f"shop {sid} stock → {iid}")
    assert not missing, "broken shop stock:\n" + "\n".join(missing)


def test_recipe_item_refs(reg: DataRegistry):
    if not reg.recipes:
        pytest.skip("no recipes")
    missing: List[str] = []
    for rid, recipe in reg.recipes.items():
        out = recipe.get("output") or recipe.get("result") or recipe.get("item")
        if isinstance(out, dict):
            out = out.get("id")
        if out and out not in reg.items and out not in reg.cards:
            missing.append(f"{rid} output → {out}")
        inputs = recipe.get("inputs") or {}
        if isinstance(inputs, dict):
            for mid in inputs:
                if mid not in reg.items and mid not in reg.cards:
                    missing.append(f"{rid} input → {mid}")
        for mat in recipe.get("materials") or recipe.get("ingredients") or []:
            mid = mat.get("id") if isinstance(mat, dict) else mat
            if mid and mid not in reg.items and mid not in reg.cards:
                missing.append(f"{rid} mat → {mid}")
    assert not missing, "broken recipes:\n" + "\n".join(missing)


def test_skill_learn_item_refs(reg: DataRegistry):
    """learn.cost_items / learn.items if present must exist."""
    missing: List[str] = []
    for sid, sk in reg.skills.items():
        learn = sk.get("learn") or {}
        if not isinstance(learn, dict):
            continue
        for key in ("cost_items", "items", "item", "require_item"):
            val = learn.get(key)
            if isinstance(val, str) and val not in reg.items:
                missing.append(f"{sid}.learn.{key} → {val}")
            elif isinstance(val, list):
                for v in val:
                    iid = v.get("id") if isinstance(v, dict) else v
                    if isinstance(iid, str) and iid not in reg.items and iid not in (
                        "self",
                        "discovery",
                        "master",
                        "rank",
                    ):
                        # list of methods uses strings like discovery — skip non-item
                        if key in ("cost_items", "items", "require_item") or (
                            isinstance(v, dict) and v.get("id")
                        ):
                            if iid not in reg.items:
                                missing.append(f"{sid}.learn.{key} → {iid}")
            elif isinstance(val, dict):
                for iid in val:
                    if iid not in reg.items:
                        missing.append(f"{sid}.learn.{key} → {iid}")
    assert not missing, "broken skill learn items:\n" + "\n".join(missing)


def test_skill_requires_refs(reg: DataRegistry):
    missing: List[str] = []
    for sid, sk in reg.skills.items():
        for pre in sk.get("requires") or sk.get("prereq") or sk.get("prerequisites") or []:
            pid = pre if isinstance(pre, str) else (pre.get("id") if isinstance(pre, dict) else None)
            if pid and pid not in reg.skills:
                missing.append(f"{sid} requires → {pid}")
    assert not missing, "broken skill requires:\n" + "\n".join(missing)


def test_dungeon_area_and_boss_refs(reg: DataRegistry):
    cfg = reg.dungeons_cfg or {}
    dungeons = cfg.get("dungeons") or []
    if not dungeons:
        pytest.skip("no dungeons cfg")
    missing: List[str] = []
    for d in dungeons:
        if not isinstance(d, dict):
            continue
        did = d.get("id", "?")
        aid = d.get("area_id") or d.get("area")
        if aid and aid not in reg.areas:
            missing.append(f"dungeon {did} area_id → {aid}")
        bid = d.get("boss_id") or d.get("boss")
        if bid and bid not in reg.monsters:
            missing.append(f"dungeon {did} boss → {bid}")
        for it in (d.get("rewards") or {}).get("items") or []:
            iid = it.get("id") if isinstance(it, dict) else it
            if iid and iid not in reg.items:
                missing.append(f"dungeon {did} reward → {iid}")
    # escape items
    for it in (cfg.get("escape") or {}).get("items") or []:
        iid = it.get("id") if isinstance(it, dict) else it
        if iid and iid not in reg.items:
            missing.append(f"escape item → {iid}")
    assert not missing, "broken dungeon refs:\n" + "\n".join(missing)


def test_rarity_tiers_present(reg: DataRegistry):
    tiers = (reg.rarity or {}).get("tiers") or reg.rarity or {}
    # accept either nested tiers or top-level id map
    assert tiers, "rarity config empty"


def test_no_duplicate_skill_ids_across_trees(reg: DataRegistry):
    # loader already merges; ensure each skill has id matching key
    bad = [sid for sid, sk in reg.skills.items() if sk.get("id") and sk.get("id") != sid]
    assert not bad, f"skill id mismatches: {bad[:10]}"


def test_status_catalog_core_ids(reg: DataRegistry):
    assert reg.statuses, "status catalog empty"
    for sid in ("poison", "burn", "freeze", "stun", "shock"):
        assert sid in reg.statuses, f"missing status {sid}"
        st = reg.statuses[sid]
        assert st.get("name"), f"{sid} missing name"
        assert "duration" in st or st.get("duration") is not None


def test_companion_templates_if_present(reg: DataRegistry):
    party = reg.party or {}
    comps = party.get("companions") or party.get("templates") or {}
    if not comps:
        pytest.skip("no companions")
    if isinstance(comps, list):
        for c in comps:
            assert c.get("id"), "companion missing id"
    elif isinstance(comps, dict):
        assert len(comps) >= 1

"""D1–D2 per-monster drops · G1 gear/mat content."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.craft import craft, list_recipes
from game.domain.equipment import add_item
from game.domain.inventory_sys import build_combat_loot_table, item_category
from game.domain.monster_drops import (
    monster_has_drop_table,
    mon_drop_entries,
    rate_to_chance,
    roll_monster_table_drops,
)


class _Ok:
    def random(self) -> float:
        return 0.0

    def randint(self, a: int, b: int) -> int:
        return a

    def randrange(self, n: int) -> int:
        return 0


def test_rate_bands():
    assert rate_to_chance("common") > rate_to_chance("rare")
    assert rate_to_chance("always") >= 0.99
    assert 0 < rate_to_chance(0.1) < 1


def test_forest_cave_monsters_have_tables():
    reg = DataRegistry.load(DATA_DIR)
    for mid in (
        "goblin_hunter",
        "forest_wolf",
        "wood_ent",
        "forest_wraith",
        "cave_bat",
        "dark_slime",
        "shadow_wraith",
        "abyss_lurker",
    ):
        m = reg.monsters[mid]
        assert monster_has_drop_table(m), mid
        assert mon_drop_entries(m), mid


def test_all_monsters_have_drop_tables():
    """1.26: every mon (incl. bosses) has drops and/or card_id."""
    reg = DataRegistry.load(DATA_DIR)
    missing = []
    bad_items = []
    for mid, m in (reg.monsters or {}).items():
        if not monster_has_drop_table(m):
            missing.append(mid)
            continue
        for e in mon_drop_entries(m):
            iid = str(e.get("item") or "")
            if iid not in (reg.items or {}) and iid not in (reg.cards or {}):
                bad_items.append((mid, iid))
    assert not missing, f"no drop table: {missing}"
    assert not bad_items, f"bad drop ids: {bad_items[:10]}"


def test_area_packs_roll_distinct_mats():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ap", "warrior", "เมษ")

    class Always(random.Random):
        def random(self) -> float:
            return 0.0

        def randint(self, a: int, b: int) -> int:
            return a

    samples = {
        "rock_golem": "stone_chip",
        "sand_scorpion": "scorpion_stinger",
        "marsh_leech": "leech_sac",
        "city_rat": "rat_tail",
        "void_mote": "void_ash",
        "crystal_mite": "crystal_dust",
    }
    for mid, want in samples.items():
        rolled = roll_monster_table_drops(p, reg.monsters[mid], reg, Always(1))
        ids = [r["id"] for r in rolled]
        assert want in ids, (mid, ids)


def test_roll_wolf_always_with_ok_rng():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dw", "warrior", "เมษ")
    mon = dict(reg.monsters["forest_wolf"])
    # force all rates hit
    class Always(random.Random):
        def random(self) -> float:
            return 0.0

    rolled = roll_monster_table_drops(p, mon, reg, Always(1))
    ids = [r["id"] for r in rolled]
    assert "wolf_fang" in ids


def test_build_loot_includes_mon_mat():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "dl", "warrior", "เมษ")
    mon = dict(reg.monsters["goblin_hunter"])
    found = False
    for seed in range(40):
        loot = build_combat_loot_table(p, mon, reg, random.Random(seed))
        ids = [str(d.get("id")) for d in loot]
        if "goblin_scrap" in ids or "bandit_knife" in ids or "ash_club" in ids:
            found = True
            break
    assert found


def test_g1_items_exist_and_slots():
    reg = DataRegistry.load(DATA_DIR)
    assert item_category("leather_cap", reg) == "equipment"
    assert item_category("iron_greaves", reg) == "equipment"
    assert item_category("hardened_boots", reg) == "equipment"
    assert item_category("scout_spear", reg) == "equipment"
    assert item_category("woodsman_axe", reg) == "equipment"
    assert item_category("wolf_fang", reg) == "material"
    for iid in (
        "leather_cap",
        "chain_coif",
        "iron_greaves",
        "ranger_leggings",
        "hardened_boots",
        "iron_sabatons",
        "scout_spear",
        "woodsman_axe",
        "ash_club",
    ):
        it = reg.items[iid]
        assert it.get("slot") or it.get("kind") == "equipment"


def test_slot_coverage_improved():
    reg = DataRegistry.load(DATA_DIR)
    from game.domain.equipment import normalize_slot, EQUIP_SLOTS

    counts = {s: 0 for s in EQUIP_SLOTS}
    for it in reg.items.values():
        ns = normalize_slot(str(it.get("slot") or ""))
        if ns in counts:
            counts[ns] += 1
    assert counts["legs"] >= 3
    assert counts["feet"] >= 3
    assert counts["head"] >= 3
    assert counts["main_hand"] >= 10


def test_craft_spear_from_mon_mat():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cs", "warrior", "เมษ")
    p["level"] = 5
    p["location"] = "mountain_rock"
    p["money_world"] = 200
    add_item(p, "ent_bark", reg)
    add_item(p, "upgrade_mat", reg)
    add_item(p, "upgrade_mat", reg)
    assert any(r.get("id") == "craft_scout_spear" for r in list_recipes(reg, p))
    msg = craft(p, reg, "craft_scout_spear", rng=_Ok())  # type: ignore[arg-type]
    assert "สำเร็จ" in msg
    assert "scout_spear" in (p.get("inventory_ids") or [])


def test_bound_card_id_on_wolf():
    reg = DataRegistry.load(DATA_DIR)
    m = reg.monsters["forest_wolf"]
    # IC2+: mon-bound card (not shared card_wind)
    cid = str(m.get("card_id") or "")
    assert cid.startswith("card_")
    assert cid in ("card_forest_wolf", "card_wind")
    entries = mon_drop_entries(m)
    assert any(e.get("item") == cid for e in entries)


def test_pick_monster_carries_drop_table():
    """Hotfix 1.27: runtime mon must keep drops/card_id for victory loot."""
    from game.domain.combat import pick_monster
    from game.domain.boss import spawn_boss

    reg = DataRegistry.load(DATA_DIR)
    mon = pick_monster(reg, "dark_forest", random.Random(7))
    assert mon.get("drops"), mon.get("id")
    assert mon.get("card_id") or any(
        str(d.get("item") or "").startswith("card_") for d in (mon.get("drops") or [])
    )
    # loot table sees mon mats
    p = create_player(reg, "pm", "warrior", "เมษ")
    found = False
    for seed in range(50):
        loot = build_combat_loot_table(p, mon, reg, random.Random(seed))
        ids = [str(d.get("id")) for d in loot]
        # forest pool mon mats
        if any(
            x in ids
            for x in (
                "goblin_scrap",
                "wolf_fang",
                "ent_bark",
                "wraith_dust",
                "herb_bundle",
            )
        ):
            found = True
            break
    assert found, "pick_monster mon should produce mon-table loot"

    boss = spawn_boss(reg, "dark_forest", random.Random(1))
    assert boss and boss.get("boss")
    assert boss.get("drops"), "boss must carry drops"
    assert boss.get("card_id")


def test_loot_rehydrates_from_registry_if_stripped():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "rh", "warrior", "เมษ")
    bare = {"id": "forest_wolf", "name": "Wolf", "level": 3, "boss": False}
    class Always(random.Random):
        def random(self) -> float:
            return 0.0
        def randint(self, a: int, b: int) -> int:
            return a
        def randrange(self, n: int) -> int:
            return 0
    loot = build_combat_loot_table(p, bare, reg, Always(1))
    ids = [str(d.get("id")) for d in loot]
    assert "wolf_fang" in ids

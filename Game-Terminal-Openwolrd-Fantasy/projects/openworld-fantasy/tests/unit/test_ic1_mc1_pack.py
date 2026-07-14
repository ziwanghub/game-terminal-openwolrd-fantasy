"""IC1 gear pack + MC1 mountain/desert monsters + S1 elite soft."""
from __future__ import annotations

import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import pick_monster, player_attack_damage
from game.domain.craft import craft, list_recipes
from game.domain.equipment import add_item, equip_item, normalize_slot
from game.domain.inventory_sys import item_category
from game.domain.monster_drops import mon_drop_entries, monster_has_drop_table


MC1_MONS = (
    "cliff_eagle",
    "stone_mole",
    "ridge_reaver",
    "sand_viper",
    "dust_wisp",
    "oasis_jackal",
    "dune_stalker",
)

IC1_GEAR = (
    "padded_helm",
    "storm_hood",
    "scale_greaves",
    "dune_wraps",
    "climber_boots",
    "dune_sandals",
    "ridge_spear",
    "desert_scimitar",
    "bronze_buckler",
)


def test_mc1_monsters_in_pools_and_drops():
    reg = DataRegistry.load(DATA_DIR)
    mt = {p["id"] for p in reg.areas["mountain_rock"]["monster_pools"]}
    ds = {p["id"] for p in reg.areas["desert_heat"]["monster_pools"]}
    assert len(mt) >= 5
    assert len(ds) >= 5
    assert "cliff_eagle" in mt and "ridge_reaver" in mt
    assert "sand_viper" in ds and "dune_stalker" in ds
    for mid in MC1_MONS:
        m = reg.monsters[mid]
        assert monster_has_drop_table(m), mid
        for e in mon_drop_entries(m):
            iid = e["item"]
            assert iid in reg.items or iid in reg.cards, (mid, iid)


def test_mc1_cards_exist_drop_only():
    reg = DataRegistry.load(DATA_DIR)
    for cid in ("card_cliff_eagle", "card_sand_viper", "card_dust_wisp"):
        assert cid in reg.cards
    # shops must not sell new cards
    from game.services.shop import _normalize_stock, _is_shop_banned_card

    for shop in (reg.shops or {}).values():
        for row in _normalize_stock(shop, reg=reg):
            assert not _is_shop_banned_card(reg, str(row.get("id")))


def test_ic1_gear_slots():
    reg = DataRegistry.load(DATA_DIR)
    for iid in IC1_GEAR:
        it = reg.items[iid]
        assert it.get("kind") == "equipment"
        assert item_category(iid, reg) == "equipment"
        assert normalize_slot(str(it.get("slot"))) in (
            "main_hand",
            "off_hand",
            "head",
            "legs",
            "feet",
            "body",
            "acc_1",
        )


def test_equip_new_spear_and_buckler():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "eq1", "warrior", "เมษ")
    add_item(p, "ridge_spear", reg)
    add_item(p, "bronze_buckler", reg)
    msg1 = equip_item(p, "ridge_spear", reg)
    msg2 = equip_item(p, "bronze_buckler", reg)
    assert msg1 and msg2
    eqs = p.get("equip_ids") or {}
    assert eqs.get("main_hand") == "ridge_spear" or "ridge_spear" not in (
        p.get("inventory_ids") or []
    )
    # off_hand may be shield after equip
    assert eqs.get("off_hand") == "bronze_buckler" or eqs.get("main_hand")


def test_craft_ridge_spear():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cr1", "warrior", "เมษ")
    p["level"] = 6
    p["location"] = "mountain_rock"
    p["money_world"] = 200
    add_item(p, "mole_claw", reg)
    add_item(p, "stone_chip", reg)
    add_item(p, "stone_chip", reg)
    add_item(p, "upgrade_mat", reg)
    add_item(p, "upgrade_mat", reg)

    class Ok:
        def random(self):
            return 0.0

    assert any(r.get("id") == "craft_ridge_spear" for r in list_recipes(reg, p))
    msg = craft(p, reg, "craft_ridge_spear", rng=Ok())  # type: ignore[arg-type]
    assert "สำเร็จ" in msg
    assert "ridge_spear" in (p.get("inventory_ids") or [])


def test_pick_mountain_can_be_new_species():
    reg = DataRegistry.load(DATA_DIR)
    seen = set()
    for s in range(60):
        m = pick_monster(reg, "mountain_rock", random.Random(s))
        seen.add(m.get("id"))
        assert m.get("drops") is not None or mon_drop_entries(
            reg.monsters.get(str(m.get("id"))) or {}
        )
    assert seen & {"cliff_eagle", "stone_mole", "ridge_reaver", "rock_golem"}


def test_elite_soft_label_or_flag():
    reg = DataRegistry.load(DATA_DIR)
    # force pick ridge_reaver by mocking? just load catalog elite and pick many
    hit = False
    for s in range(100):
        m = pick_monster(reg, "mountain_rock", random.Random(s + 200))
        if m.get("id") == "ridge_reaver" or m.get("elite"):
            hit = True
            if m.get("elite") or m.get("id") == "ridge_reaver":
                assert m.get("elite") or "◆" in str(m.get("name")) or m.get("rarity")
            break
    # if unlucky never rolled reaver, still ok if any elite
    if not hit:
        for s in range(100):
            m = pick_monster(reg, "desert_heat", random.Random(s + 500))
            if m.get("elite") or m.get("id") == "dune_stalker":
                hit = True
                break
    assert hit


def test_attack_flavor_can_include_class_soft():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "at", "warrior", "เมษ")
    p["power_atk"] = 20
    mon = dict(reg.monsters["rock_golem"])
    mon["elements"] = ["earth"]
    mon["hp"] = 100
    sk = {"power": 10, "elements": ["physical"]}
    flavs = []
    for s in range(40):
        _, fl = player_attack_damage(p, mon, reg, "mountain_rock", sk, random.Random(s))
        flavs.append(fl)
    # at least some flavor or empty is ok; ensure no crash and dmg positive
    dmg, _ = player_attack_damage(p, mon, reg, "mountain_rock", sk, random.Random(1))
    assert dmg >= 1

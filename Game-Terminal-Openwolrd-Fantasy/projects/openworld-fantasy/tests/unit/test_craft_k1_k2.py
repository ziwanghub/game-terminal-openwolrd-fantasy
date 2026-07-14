"""Craft K1 success/fail · K2 material quality bonus."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.craft import (
    craft,
    craft_chance_label,
    craft_success_chance,
    material_quality_mult,
    recipe_chance_label,
)
from game.domain.equipment import add_item


class _Rng:
    """Deterministic: first random() = a, second = b, then 0."""

    def __init__(self, *values: float):
        self._vals = list(values)
        self._i = 0

    def random(self) -> float:
        if self._i < len(self._vals):
            v = self._vals[self._i]
            self._i += 1
            return v
        return 0.0


def test_craft_rules_loaded():
    reg = DataRegistry.load(DATA_DIR)
    assert reg.craft_rules
    assert "base_success" in reg.craft_rules


def test_success_always_with_low_roll():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ok", "warrior", "เมษ")
    add_item(p, "potion_hp_small", reg)
    add_item(p, "potion_hp_small", reg)
    p["money_world"] = 100
    msg = craft(p, reg, "craft_potion_bundle", rng=_Rng(0.0))
    assert "สำเร็จ" in msg
    assert "potion_hp" in (p.get("inventory_ids") or [])


def test_soft_fail_refunds_partial():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "fail", "warrior", "เมษ")
    p["level"] = 10
    p["location"] = "ancient_city"  # K3 forge
    p["money_world"] = 500
    add_item(p, "iron_sword", reg, rarity="uncommon")
    for _ in range(3):
        add_item(p, "upgrade_mat", reg, rarity="common")
    add_item(p, "rare_mat", reg, rarity="common")
    money_before = p["money_world"]
    # roll 0.99 fail · 0.99 avoid hard → soft fail
    msg = craft(p, reg, "craft_steel_blade", rng=_Rng(0.99, 0.99))
    assert "ล้มเหลว" in msg
    assert "steel_blade" not in (p.get("inventory_ids") or [])
    # soft refund: some money and/or mats back
    assert int(p["money_world"]) > money_before - 120 or any(
        x in (p.get("inventory_ids") or []) for x in ("upgrade_mat", "iron_sword", "rare_mat")
    )


def test_hard_fail_no_product():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "hard", "warrior", "เมษ")
    p["level"] = 10
    p["location"] = "ancient_city"  # K3 forge
    p["money_world"] = 500
    add_item(p, "iron_sword", reg, rarity="uncommon")
    for _ in range(3):
        add_item(p, "upgrade_mat", reg)
    add_item(p, "rare_mat", reg)
    # fail main + hard branch (second random low for hard_chance)
    msg = craft(p, reg, "craft_steel_blade", rng=_Rng(0.99, 0.0))
    assert "ล้มเหลว" in msg
    assert "steel_blade" not in (p.get("inventory_ids") or [])


def test_k2_higher_mat_quality_boosts_chance():
    reg = DataRegistry.load(DATA_DIR)
    low = create_player(reg, "lo", "warrior", "เมษ")
    high = create_player(reg, "hi", "warrior", "เมษ")
    low["level"] = high["level"] = 10
    low["money_world"] = high["money_world"] = 500
    recipe = reg.recipes["craft_steel_blade"]

    # min: uncommon sword + common mats
    add_item(low, "iron_sword", reg, rarity="uncommon")
    for _ in range(3):
        add_item(low, "upgrade_mat", reg, rarity="common")
    add_item(low, "rare_mat", reg, rarity="common")

    # better: rare sword + rare mats
    add_item(high, "iron_sword", reg, rarity="rare")
    for _ in range(3):
        add_item(high, "upgrade_mat", reg, rarity="rare")
    add_item(high, "rare_mat", reg, rarity="rare")

    m_lo = material_quality_mult(low, recipe, reg)
    m_hi = material_quality_mult(high, recipe, reg)
    assert m_hi > m_lo
    c_lo = craft_success_chance(low, recipe, reg)
    c_hi = craft_success_chance(high, recipe, reg)
    assert c_hi > c_lo


def test_chance_labels_soft():
    assert craft_chance_label(0.9) == "โอกาสสูง"
    assert craft_chance_label(0.6) == "โอกาสปานกลาง"
    assert craft_chance_label(0.3) == "เสี่ยงสูง"


def test_recipe_label_not_ready():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "nr", "warrior", "เมษ")
    r = reg.recipes["craft_steel_blade"]
    assert recipe_chance_label(p, r, reg) == "ยังไม่พร้อม"


def test_sacred_craft_lower_base_than_common():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "tier", "warrior", "เมษ")
    p["level"] = 20
    p["money_world"] = 9999
    # potion bundle = common-ish
    add_item(p, "potion_hp_small", reg)
    add_item(p, "potion_hp_small", reg)
    c_common = craft_success_chance(p, reg.recipes["craft_potion_bundle"], reg)

    p2 = create_player(reg, "tier2", "warrior", "เมษ")
    p2["level"] = 20
    p2["money_world"] = 9999
    add_item(p2, "steel_blade", reg, rarity="rare")
    for _ in range(3):
        add_item(p2, "upgrade_mat", reg, rarity="rare")
    for _ in range(2):
        add_item(p2, "rare_mat", reg, rarity="rare")
    c_sacred = craft_success_chance(p2, reg.recipes["craft_thorn_blade"], reg)
    assert c_common > c_sacred

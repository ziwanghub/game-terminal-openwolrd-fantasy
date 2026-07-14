import random

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, recompute_stats
from game.domain.party import member_from_template
from game.domain.rarity import (
    all_tiers,
    format_rarity_tag,
    rarity_stat_mult,
    roll_rarity,
    scale_stat,
    scaled_item_stats,
)


def test_tiers_loaded():
    reg = DataRegistry.load(DATA_DIR)
    tiers = all_tiers(reg)
    assert len(tiers) >= 7
    ids = [t["id"] for t in tiers]
    assert "common" in ids
    assert "archdivine" in ids or "divine" in ids
    assert rarity_stat_mult(reg, "legendary") > rarity_stat_mult(reg, "common")


def test_scale_stats_by_rarity():
    reg = DataRegistry.load(DATA_DIR)
    assert scale_stat(10, "common", reg) == 10
    assert scale_stat(10, "rare", reg) > 10
    assert scale_stat(10, "divine", reg) > scale_stat(10, "rare", reg)


def test_equip_rare_stronger_than_common():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "r1", "warrior", "เมษ")
    add_item(p, "iron_sword", reg, rarity="common")
    equip_item(p, "iron_sword", reg)
    recompute_stats(p, reg)
    atk_c = int(p["bonus_atk"])

    p2 = create_player(reg, "r2", "warrior", "เมษ")
    add_item(p2, "iron_sword", reg, rarity="legendary")
    equip_item(p2, "iron_sword", reg)
    recompute_stats(p2, reg)
    atk_l = int(p2["bonus_atk"])
    assert atk_l > atk_c


def test_companion_rarity_scales():
    reg = DataRegistry.load(DATA_DIR)
    t = {
        "id": "t_test",
        "name": "ทดสอบ",
        "kind": "beast",
        "bonus_atk": 10,
        "bonus_max_hp": 20,
        "bonus_max_mana": 0,
        "rarity": "common",
    }
    m1 = member_from_template(t, reg, rarity="common")
    m2 = member_from_template(t, reg, rarity="divine")
    assert m2["bonus_atk"] > m1["bonus_atk"]
    assert m2["rarity"] == "divine"


def test_roll_rarity_weights():
    reg = DataRegistry.load(DATA_DIR)
    rng = random.Random(42)
    rolls = [roll_rarity(reg, rng, pool="drop") for _ in range(80)]
    assert "common" in rolls or "uncommon" in rolls
    # archdivine should be rare
    assert rolls.count("archdivine") < rolls.count("common") + rolls.count("uncommon")


def test_format_tag():
    reg = DataRegistry.load(DATA_DIR)
    tag = format_rarity_tag(reg, "sacred")
    assert "ศักดิ์สิทธิ์" in tag or "sacred" in tag.lower()


def test_scaled_item_stats():
    reg = DataRegistry.load(DATA_DIR)
    it = reg.items.get("iron_sword") or {"atk": 6}
    s = scaled_item_stats(it, "rare", reg, upgrade_level=0, slot="weapon")
    assert s["atk"] >= int(it.get("atk") or 0)


def test_display_item_name_changes():
    reg = DataRegistry.load(DATA_DIR)
    from game.domain.rarity import display_item_name

    common = display_item_name("ดาบเหล็ก", "common", reg)
    legend = display_item_name("ดาบเหล็ก", "legendary", reg)
    assert "ดาบเหล็ก" in common
    assert "ตำนาน" in legend
    assert legend != common


def test_monster_rarity_scales_hp():
    reg = DataRegistry.load(DATA_DIR)
    from game.domain.combat import pick_monster
    from game.domain.rarity import apply_rarity_to_enemy

    mon = {
        "id": "t",
        "name": "ทดสอบ",
        "base_name": "ทดสอบ",
        "hp": 100,
        "max_hp": 100,
        "atk": 10,
        "xp_mult": 1.0,
        "attack_profiles": [{"power": 10}],
    }
    strong = apply_rarity_to_enemy(dict(mon), reg, "divine")
    weak = apply_rarity_to_enemy(dict(mon), reg, "common")
    assert strong["hp"] > weak["hp"]
    assert strong["atk"] > weak["atk"]
    assert "เทพ" in strong["name"] or strong["rarity"] == "divine"


def test_sell_price_scales_with_rarity():
    reg = DataRegistry.load(DATA_DIR)
    from game.domain.balance import sell_price

    p = create_player(reg, "sp", "warrior", "เมษ")
    low = sell_price(100, reg, p, rarity="common")
    high = sell_price(100, reg, p, rarity="legendary")
    # legendary has higher buy ref but also higher tax — net still usually >= common
    # with insurance; at least buy-scaled path differs
    from game.domain.balance import sell_breakdown

    bl = sell_breakdown(100, reg, p, rarity="common")
    bh = sell_breakdown(100, reg, p, rarity="legendary")
    assert bh["buy_ref"] > bl["buy_ref"]
    assert bh["tax_rate"] > bl["tax_rate"]
    assert high >= 1 and low >= 1


def test_price_insurance_and_tax():
    reg = DataRegistry.load(DATA_DIR)
    from game.domain.balance import sell_breakdown

    p = create_player(reg, "ins", "warrior", "เมษ")
    bd = sell_breakdown(1000, reg, p, rarity="mythic")
    assert bd["tax_rate"] >= 0.3
    assert bd["net"] >= bd["floor"] or bd["net"] >= 1
    assert bd["insured"] >= bd["floor"]


def test_specialty_shops_exist():
    reg = DataRegistry.load(DATA_DIR)
    assert "rare_exchange" in reg.shops
    assert "legend_pavilion" in reg.shops
    assert int(reg.shops["legend_pavilion"].get("min_rarity_rank") or 0) >= 5
    # legend pavilion: system stock empty — high gear from drop → player market
    assert list(reg.shops["legend_pavilion"].get("stock") or []) == []
    from game.services.shop import shop_rank_window

    lo, hi = shop_rank_window(reg.shops["rare_exchange"])
    # material exchange: uncommon–sacred window (no legendary system stock)
    assert lo <= 3 and hi >= 4


def test_shop_stock_normalize():
    from game.services.shop import _normalize_stock

    reg = DataRegistry.load(DATA_DIR)
    shop = reg.shops.get("city_armory") or {}
    stock = _normalize_stock(shop)
    assert stock
    assert any(isinstance(x.get("rarity"), str) for x in stock if x.get("rarity"))


def test_monster_fixed_rarity():
    reg = DataRegistry.load(DATA_DIR)
    mon = reg.monsters.get("abyss_lurker") or {}
    assert mon.get("rarity") in ("sacred", "rare", "legendary", "uncommon") or mon
    # if data set
    if "abyss_lurker" in reg.monsters:
        assert reg.monsters["abyss_lurker"].get("rarity") == "sacred"


def test_remove_inventory_at_index():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "rm", "mage", "เมถุน")
    p["inventory_ids"] = []
    p["inventory_rarities"] = []
    p["inventory"] = []
    add_item(p, "iron_sword", reg, rarity="common")
    add_item(p, "iron_sword", reg, rarity="legendary")
    from game.domain.rarity import remove_inventory_at_index, rarity_of_inventory_index

    assert rarity_of_inventory_index(p, 1) == "legendary"
    removed = remove_inventory_at_index(p, 1, reg)
    assert removed and removed[1] == "legendary"
    assert len(p["inventory_ids"]) == 1


def test_craft_requires_input_rarity():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "cr", "warrior", "เมษ")
    p["level"] = 10
    p["location"] = "ancient_city"  # K3 forge station
    p["money_world"] = 5000
    # only common iron sword — steel craft needs uncommon
    add_item(p, "iron_sword", reg, rarity="common")
    for _ in range(5):
        add_item(p, "upgrade_mat", reg, rarity="common")
        add_item(p, "rare_mat", reg, rarity="common")
    from game.domain.craft import craft

    msg = craft(p, reg, "craft_steel_blade")
    assert "ไม่พอ" in msg or "ระดับ" in msg
    # now with uncommon sword
    add_item(p, "iron_sword", reg, rarity="uncommon")

    class _Ok:
        def random(self):
            return 0.0

    msg2 = craft(p, reg, "craft_steel_blade", rng=_Ok())  # type: ignore[arg-type]
    assert "สำเร็จ" in msg2

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, equip_item, recompute_stats, socket_card


def test_equip_and_socket_raises_atk():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "eq", "warrior", "สิงห์")
    base = int(p["bonus_atk"])
    add_item(p, "iron_sword", reg)
    msg = equip_item(p, "iron_sword", reg)
    assert "สวม" in msg
    assert int(p["bonus_atk"]) >= base + 6
    add_item(p, "card_fire", reg)
    msg2 = socket_card(p, "main_hand", 0, "card_fire", reg)
    assert "ใส่" in msg2
    assert int(p["bonus_atk"]) >= base + 6 + 4
    assert "fire" in (p.get("gear_tags") or [])
    assert any(e.get("status") == "burn" for e in (p.get("on_hit_effects") or []))
    assert (p.get("equip_ids") or {}).get("main_hand") == "iron_sword"


def test_cards_and_shops_loaded():
    reg = DataRegistry.load(DATA_DIR)
    assert "card_fire" in reg.cards
    assert "traveling_merchant" in reg.shops
    assert "iron_sword" in reg.items

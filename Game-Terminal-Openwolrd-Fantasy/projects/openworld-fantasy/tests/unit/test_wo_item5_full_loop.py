"""WO-ITEM-5: Full-loop playtest harness (loot → bag → sell → craft → equip → party)."""
from __future__ import annotations

import random
from collections import Counter

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.balance import sell_price
from game.domain.bag_sell import compute_sell_offer
from game.domain.character import create_player
from game.domain.companion_decision_engine import decide_for_tests
from game.domain.equipment import add_item, equip_item, recompute_stats
from game.domain.inventory_sys import build_combat_loot_table
from game.domain.monster_drops import mon_drop_entries
from game.domain.combat_identity import weakness_lite_hint_lines


def _thick_mons(reg: DataRegistry, *, n: int = 4):
    out = []
    for mid, mon in reg.monsters.items():
        if mon.get("boss"):
            continue
        rows = len(mon_drop_entries(mon))
        if rows >= 3:
            out.append((rows, mid))
    out.sort(reverse=True)
    return out[:n]


def test_full_loop_loot_identity_over_generic():
    """Farm thick-table mons: mon-table lines should dominate generic reserve."""
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "i5a", "warrior", "เมษ")
    thick = _thick_mons(reg, n=5)
    assert thick, "need thick mon tables"
    mon_n = gen_n = 0
    hints = 0
    total = 0
    for _rows, mid in thick:
        mon = dict(reg.monsters[mid])
        mon["level"] = max(2, int(mon.get("level") or 2))
        for i in range(50):
            loot = build_combat_loot_table(p, mon, reg, random.Random(i + hash(mid) % 997))
            for d in loot:
                total += 1
                note = str(d.get("note") or "")
                src = str(d.get("source") or "")
                if "สำรอง" in note or src == "สำรองสนาม":
                    gen_n += 1
                elif src == "จากมอน" or "ชิ้นส่วน" in note or "จากมอน" in note:
                    mon_n += 1
                if any(
                    k in note
                    for k in ("จากมอน", "ชิ้นส่วน", "สำรอง", "จากบอส", "การ์ด", "คราฟ")
                ):
                    hints += 1
                assert "%" not in note
    assert total > 0
    # identity: mon table clearly ahead of generic soft reserve
    assert mon_n > gen_n
    assert gen_n / max(1, mon_n + gen_n) < 0.35
    assert hints / total >= 0.90


def test_empty_table_soft_floor_and_economy_sink():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "i5b", "warrior", "เมษ")
    empty = {"id": "empty_i5", "name": "x", "level": 1, "drops": [], "elements": []}
    any_loot = False
    for i in range(40):
        if build_combat_loot_table(p, empty, reg, random.Random(i)):
            any_loot = True
            break
    assert any_loot

    base = 50
    mat = sell_price(
        base, reg, p, rarity="common", item_kind="material", item_id="upgrade_mat"
    )
    eq = sell_price(
        base, reg, p, rarity="common", item_kind="equipment", item_id="iron_sword"
    )
    assert mat < eq
    # soft sink: not brutal — farm still worth (mat >= ~half equip path)
    assert mat >= max(1, int(eq * 0.45))
    offer = compute_sell_offer(p, reg, "upgrade_mat", "common", qty=1)
    assert offer is not None and int(offer["unit_price"]) >= 1


def test_mid_gear_tone_and_set_loop():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "i5c", "warrior", "เมษ")
    blade = reg.items.get("mid_forest_thorn_blade") or {}
    mail = reg.items.get("mid_forest_bark_mail") or {}
    assert blade and mail
    # soft tone: not bare "mid ดง"
    for it in (blade, mail):
        desc = str(it.get("desc") or "")
        assert "เซ็ต" in desc or "แนว" in desc or "ดง" in desc
        assert "mid ดง" not in desc  # WO-ITEM-5 polish: richer flavor
    add_item(p, "mid_forest_thorn_blade", reg, rarity="uncommon")
    add_item(p, "mid_forest_bark_mail", reg, rarity="uncommon")
    p["equip_ids"] = {}
    equip_item(p, "mid_forest_thorn_blade", reg)
    equip_item(p, "mid_forest_bark_mail", reg)
    recompute_stats(p, reg)
    assert p.get("active_sets")
    assert p.get("gear_primary_element") == "nature" or "nature" in (
        p.get("gear_tags") or []
    )


def test_party_priority_and_appraisal_soft():
    """Party assist priority + mon weakness soft (S+) without % dump."""
    reg = DataRegistry.load(DATA_DIR)
    # P0 crisis → heal-ish
    d0 = decide_for_tests(hp_ratio=0.15, mon_ratio=0.9, bond=70, role="support")
    assert d0.priority == 0 or str(d0.action) in ("heal", "cleanse", "ACT_HEAL", "ACT_CLEANSE") or getattr(
        d0, "act", None
    ) is not None
    # just ensure decide returns something usable
    assert d0 is not None

    p = create_player(reg, "i5d", "warrior", "เมษ")
    mon = {
        "id": "fire_dummy_i5",
        "name": "ไฟ",
        "elements": ["fire"],
        "weak_to": ["water"],
        "level": 4,
    }
    p["_appraised_targets"] = {mon["id"]: "S"}
    hints = weakness_lite_hint_lines(p, mon, reg)
    assert hints
    blob = "\n".join(hints)
    assert "%" not in blob
    assert "1.4" not in blob


def test_auto_farm_session_soft_metrics():
    """Simulate ~auto farm session: many kills, track money-ish sell + bag growth."""
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "i5e", "warrior", "เมษ")
    p["money_world"] = 100
    thick = _thick_mons(reg, n=3)
    assert thick
    src = Counter()
    for k in range(80):  # soft stand-in for 15–20 min auto slice
        _rows, mid = thick[k % len(thick)]
        mon = dict(reg.monsters[mid])
        loot = build_combat_loot_table(p, mon, reg, random.Random(k + 17))
        for d in loot:
            iid = str(d.get("id") or "")
            if not iid:
                continue
            rid = str(d.get("rarity") or "common")
            add_item(p, iid, reg, rarity=rid)
            if "สำรอง" in str(d.get("source") or "") or "สำรอง" in str(
                d.get("note") or ""
            ):
                src["generic"] += 1
            else:
                src["identity"] += 1
            # soft sell some mats for economy path
            if iid in ("upgrade_mat", "rare_mat") and k % 5 == 0:
                offer = compute_sell_offer(p, reg, iid, rid, qty=1)
                if offer:
                    p["money_world"] = int(p.get("money_world") or 0) + int(
                        offer["unit_price"]
                    )
                    src["sells"] += 1
    assert src["identity"] > src["generic"]
    # money grew but not absurd for 80 kills soft path
    assert 100 <= int(p["money_world"]) < 100 + 80 * 40
    # bag has stuff
    assert len(p.get("inventory_ids") or p.get("inventory") or []) >= 1

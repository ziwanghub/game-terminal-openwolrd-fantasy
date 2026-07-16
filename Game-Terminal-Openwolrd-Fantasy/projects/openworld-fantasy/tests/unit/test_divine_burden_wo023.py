"""WO-023: Divine Burden lite + vision rules."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.divine_burden import (
    BURDEN_MIN_RANK,
    apply_burden_tick,
    burden_gap,
    equipped_burden_pieces,
    gap_band,
    is_burden_muted,
    on_equip_burden_note,
    player_fit_rank,
    rarity_rank,
    should_block_auto_equip_relic,
    try_auto_unequip_burden,
    worst_burden_band,
)
from game.domain.needs import ensure_needs, get_needs
from game.runtime.dungeon_auto import ensure_auto_prefs


def test_legendary_rank_is_burden_tier():
    reg = DataRegistry.load(DATA_DIR)
    assert rarity_rank(reg, "legendary") >= BURDEN_MIN_RANK
    assert rarity_rank(reg, "common") < BURDEN_MIN_RANK


def test_low_level_legendary_is_strain_or_crush():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db1", "warrior", "เมษ")
    p["level"] = 1
    g = burden_gap(p, reg, "legendary")
    assert g >= 1
    assert gap_band(g) in ("strain", "crush")


def test_high_level_reduces_gap():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db2", "warrior", "เมษ")
    p["level"] = 1
    g1 = burden_gap(p, reg, "legendary")
    p["level"] = 25
    g2 = burden_gap(p, reg, "legendary")
    assert player_fit_rank(p, reg) >= 5
    assert g2 <= g1


def test_burden_tick_drains_morale():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db3", "warrior", "เมษ")
    p["level"] = 1
    ensure_needs(p)
    p["needs"]["morale"] = 80
    # equip legendary if any exists
    leg = None
    for iid, it in (reg.items or {}).items():
        if str(it.get("rarity")) == "legendary" and str(it.get("kind")) == "equipment":
            leg = str(iid)
            break
    if not leg:
        # force synthetic
        leg = "iron_sword"
        p["equip_ids"] = {"main_hand": leg}
        p["equip_rarities"] = {"main_hand": "legendary"}
    else:
        p["equip_ids"] = {"main_hand": leg}
        p["equip_rarities"] = {"main_hand": "legendary"}
    pieces = equipped_burden_pieces(p, reg)
    assert pieces, "expected burden piece at low level legendary"
    before = int(get_needs(p)["morale"])
    # several ticks
    for _ in range(5):
        apply_burden_tick(p, reg, context="field")
    after = int(get_needs(p)["morale"])
    assert after < before


def test_mute_disables_burden():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db4", "warrior", "เมษ")
    p["level"] = 1
    p["equip_ids"] = {"main_hand": "iron_sword"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    p["burden_muted"] = True
    assert is_burden_muted(p)
    assert equipped_burden_pieces(p, reg) == []
    assert worst_burden_band(p, reg) == "fit"


def test_auto_unequip_when_morale_low():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db5", "warrior", "เมษ")
    p["level"] = 1
    ensure_needs(p)
    p["needs"]["morale"] = 15
    prefs = ensure_auto_prefs(p)
    prefs["auto_unequip_burden"] = True
    prefs["morale"] = 30
    p["auto_prefs"] = prefs
    p["equip_ids"] = {"main_hand": "iron_sword"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    p["inventory_ids"] = list(p.get("inventory_ids") or [])
    notes = try_auto_unequip_burden(p, reg)
    assert notes
    assert not (p.get("equip_ids") or {}).get("main_hand")


def test_block_auto_equip_relic_default():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db6", "warrior", "เมษ")
    p["level"] = 1
    ensure_auto_prefs(p)
    assert should_block_auto_equip_relic(p, reg, "legendary") is True
    assert should_block_auto_equip_relic(p, reg, "common") is False


def test_equip_flavor_note():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db7", "warrior", "เมษ")
    p["level"] = 1
    notes = on_equip_burden_note(p, reg, rarity_id="legendary", item_name="ดาบทดสอบ")
    assert notes
    assert any("ร้อน" in n or "ภาระ" in n or "สั่น" in n or "ลม" in n for n in notes)


def test_godforge_enter_loan_exit_no_money():
    from game.services.godforge_chamber import (
        CHAMBER_RELICS,
        enter_godforge,
        exit_godforge,
        in_godforge,
        loan_relic,
        set_chamber_mode,
        spar_dummy,
    )

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db8", "warrior", "เมษ")
    p["money_world"] = 333
    enter_godforge(p, reg)
    assert in_godforge(p)
    loan_relic(p, reg, CHAMBER_RELICS[0]["id"])
    assert CHAMBER_RELICS[0]["id"] in (p.get("inventory_ids") or [])
    set_chamber_mode(p, "power")
    assert is_burden_muted(p)
    spar_dummy(p, reg)
    exit_godforge(p, reg)
    assert not in_godforge(p)
    assert CHAMBER_RELICS[0]["id"] not in (p.get("inventory_ids") or [])
    assert int(p["money_world"]) == 333


def test_relic_content_pack_exists():
    reg = DataRegistry.load(DATA_DIR)
    for iid in (
        "relic_storm_fang",
        "relic_hell_ember_blade",
        "relic_aegis_sky",
        "relic_void_whisper_ring",
    ):
        it = (reg.items or {}).get(iid) or {}
        assert it, f"missing {iid}"
        assert str(it.get("rarity")) in ("legendary", "divine")
        assert it.get("kind") == "equipment"


def test_echo_reaction_humble_and_aggro():
    from game.domain.divine_burden import apply_echo_relic_reaction

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db9", "warrior", "เมษ")
    ensure_needs(p)
    p["needs"]["morale"] = 50
    apply_echo_relic_reaction(p, "humble")
    assert int(get_needs(p)["morale"]) >= 50
    apply_echo_relic_reaction(p, "aggro")
    assert int(get_needs(p)["morale"]) < 53


def test_grant_combat_money_untouched_by_burden():
    """Economy WO-021 must not regress."""
    import random
    from game.domain.balance import grant_combat_money

    p = {
        "money_world": 0,
        "money_heaven": 0,
        "money_hell": 0,
        "world_modifiers": {},
        "equip_ids": {"main_hand": "relic_storm_fang"},
        "equip_rarities": {"main_hand": "legendary"},
        "level": 1,
    }
    lines = grant_combat_money(
        p, {"id": "w", "level": 3}, random.Random(1), auto=False
    )
    assert p["money_world"] >= 1
    assert any("เงินโลก" in x for x in lines)


# --- WO-024 polish ---


def test_echo_relic_presence_and_prompt():
    from game.domain.divine_burden import (
        entity_has_relic_presence,
        should_prompt_relic_aura,
    )
    from game.domain.world_social import build_echo_snapshot

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db10", "warrior", "เมษ")
    p["level"] = 1
    p["equip_ids"] = {"main_hand": "relic_storm_fang"}
    p["equip_rarities"] = {"main_hand": "legendary"}
    snap = build_echo_snapshot(p)
    assert snap.get("relic_presence") or entity_has_relic_presence(snap, reg)
    assert "equip_rarity_summary" in snap
    other = {
        "is_echo_snapshot": True,
        "equip_rarity_summary": {"main_hand": "legendary"},
        "relic_presence": True,
        "name": "เงาแรง",
    }
    show, why = should_prompt_relic_aura(p, other, reg)
    assert show is True
    assert why


def test_boss_drops_include_relics():
    reg = DataRegistry.load(DATA_DIR)
    forest = (reg.monsters or {}).get("boss_forest_king") or {}
    items = [str(d.get("item")) for d in (forest.get("drops") or []) if isinstance(d, dict)]
    assert "relic_storm_fang" in items
    void = (reg.monsters or {}).get("boss_void_herald") or {}
    vitems = [str(d.get("item")) for d in (void.get("drops") or []) if isinstance(d, dict)]
    assert "relic_void_whisper_ring" in vitems or "relic_hell_ember_blade" in vitems


# --- WO-025 ---


def test_relic_quest_line_exists():
    reg = DataRegistry.load(DATA_DIR)
    q1 = (reg.quests or {}).get("weight_of_storm") or {}
    assert q1
    assert "relic_storm_fang" in (q1.get("reward_items") or [])
    assert "forest_champion" in (q1.get("depends_on") or [])
    q2 = (reg.quests or {}).get("whisper_of_void_ring") or {}
    assert q2
    assert "relic_void_whisper_ring" in (q2.get("reward_items") or [])


def test_auto_pause_skips_relic_echo_when_avoid_on():
    from game.runtime.auto_farm import should_pause_sight
    from game.runtime.dungeon_auto import ensure_auto_prefs

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db11", "warrior", "เมษ")
    prefs = ensure_auto_prefs(p)
    prefs["auto_avoid_relic_echo"] = True
    p["auto_prefs"] = prefs
    sight = {
        "kind": "player",
        "label": "เงาแรง",
        "player_echo": {
            "is_echo_snapshot": True,
            "relic_presence": True,
            "equip_rarity_summary": {"main_hand": "legendary"},
        },
    }
    pause, reason = should_pause_sight(p, sight)
    assert pause is False
    assert "ออร่า" in reason or "เลี่ยง" in reason


def test_auto_pause_relic_echo_when_avoid_off():
    from game.runtime.auto_farm import should_pause_sight
    from game.runtime.dungeon_auto import ensure_auto_prefs

    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "db12", "warrior", "เมษ")
    prefs = ensure_auto_prefs(p)
    prefs["auto_avoid_relic_echo"] = False
    p["auto_prefs"] = prefs
    sight = {
        "kind": "player",
        "label": "เงาแรง",
        "player_echo": {
            "is_echo_snapshot": True,
            "relic_presence": True,
            "equip_rarity_summary": {"main_hand": "divine"},
        },
    }
    pause, reason = should_pause_sight(p, sight)
    assert pause is True
    assert "ออร่า" in reason or "เรลิก" in reason

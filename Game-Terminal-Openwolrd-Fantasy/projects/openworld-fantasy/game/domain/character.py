"""Character creation and field helpers."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from game.data_load.registry import DataRegistry
from game.domain.equipment import ensure_gear_fields, recompute_stats
from game.domain.leveling import xp_progress
from game.domain.personality import ensure_personality
from game.domain.progression import init_progression
from game.domain.stats import ensure_stats


ZODIAC = [
    ("เมษ", {"atk": 5}),
    ("พฤษภ", {"hp": 12}),
    ("เมถุน", {"mana": 12}),
    ("กรกฎ", {"pressure": 8}),
    ("สิงห์", {"atk": 4}),
    ("กันย์", {"mastery_gain": 2}),
    ("ตุลย์", {"balance": True}),
    ("พิจิก", {"deceive": 12}),
    ("ธนู", {"explore": 3}),
    ("มังกร", {"money_world": 50}),
    ("กุมภ์", {"skill_chance": 8}),
    ("มีน", {"blessing_duration": 3}),
]


def zodiac_from_date(day: int, month: int) -> str:
    # Simplified ranges (same spirit as prototype)
    ranges = [
        (3, 21, 4, 19, "เมษ"),
        (4, 20, 5, 20, "พฤษภ"),
        (5, 21, 6, 20, "เมถุน"),
        (6, 21, 7, 22, "กรกฎ"),
        (7, 23, 8, 22, "สิงห์"),
        (8, 23, 9, 22, "กันย์"),
        (9, 23, 10, 22, "ตุลย์"),
        (10, 23, 11, 21, "พิจิก"),
        (11, 22, 12, 21, "ธนู"),
        (12, 22, 1, 19, "มังกร"),
        (1, 20, 2, 18, "กุมภ์"),
        (2, 19, 3, 20, "มีน"),
    ]
    for m1, d1, m2, d2, name in ranges:
        if m1 == m2:
            if month == m1 and d1 <= day <= d2:
                return name
        elif m1 < m2:
            if (month == m1 and day >= d1) or (month == m2 and day <= d2):
                return name
        else:  # wraps year
            if (month == m1 and day >= d1) or (month == m2 and day <= d2):
                return name
    return "เมษ"


def _zodiac_bonus(name: str) -> Dict[str, Any]:
    for n, b in ZODIAC:
        if n == name:
            return dict(b)
    return {}


def create_player(
    reg: DataRegistry,
    name: str,
    occupation_id: str,
    zodiac: str,
    gender: str = "ไม่ระบุ",
    birth: str = "1/1/2000",
    world_id: str = "default",
) -> Dict[str, Any]:
    occ = reg.occupations.get(occupation_id) or next(iter(reg.occupations.values()))
    z = _zodiac_bonus(zodiac)
    world = reg.worlds.get(world_id) or {"starting_area": "dark_forest"}
    start_area = str(world.get("starting_area") or "dark_forest")
    if start_area not in reg.areas:
        start_area = next(iter(reg.areas.keys()))

    max_hp = int(occ.get("hp", 100)) + int(z.get("hp", 0))
    max_mana = int(occ.get("mana", 50)) + int(z.get("mana", 0))
    if z.get("balance"):
        max_hp += 5
        max_mana += 5

    mastery = {}
    for aid, area in reg.areas.items():
        mastery[aid] = int(area.get("mastery_start", 10))

    skill0 = str(occ.get("skill") or "basic_strike")
    player: Dict[str, Any] = {
        "save_version": 1,
        "world_id": world_id,
        "id": "",  # set on save
        "name": name or "นักผจญภัย",
        "gender": gender,
        "birth": birth,
        "zodiac": zodiac,
        "occupation_id": occ.get("id", occupation_id),
        "occupation": occ.get("name", occupation_id),
        "occ_path": occ.get("path_name") or occ.get("path") or "",
        "occ_rank_index": 0,
        "occ_rank_title": (occ.get("ranks") or [{}])[0].get("title", occ.get("name", "")),
        "stat_points": int(occ.get("points_per_level", 3)),  # may be re-rolled at create
        "stats_alloc": {
            "atk": 0,
            "defense": 0,
            "magic": 0,
            "speed": 0,
            "intelligence": 0,
            "crit": 0,
        },
        "luck_score": 0.0,
        "learn_points": 0,
        "intel_options": False,
        "blessing_flags": [],
        "emergency_blessings": [],
        "unit_class_id": None,
        "library_unlocked": False,
        "library_entries_read": [],
        "flags": {},
        "level": 1,
        "xp": 0,
        "xp_percent": 0.0,
        "hp": max_hp,
        "max_hp": max_hp,
        "mana": max_mana,
        "max_mana": max_mana,
        "pressure": int(occ.get("pressure", 10)) + int(z.get("pressure", 0)),
        "bonus_atk": int(occ.get("atk", 5)) + int(z.get("atk", 0)),
        "deceive_bonus": int(z.get("deceive", 0)),
        "mastery_gain_bonus": int(z.get("mastery_gain", 0)),
        "skill_chance_bonus": int(z.get("skill_chance", 0)),
        "money_world": 150 + int(z.get("money_world", 0)),
        "money_heaven": 8,
        "money_hell": 3,
        "inventory": ["ยา HP ขนาดเล็ก"],
        "inventory_ids": ["potion_hp_small"],
        "equip": {"weapon": None, "armor": None},
        "equip_ids": {"weapon": None, "armor": None},
        "sockets": {"weapon": [], "armor": []},
        "card_bag": [],
        "cards": [],
        "skills": [skill0, "guard_basic"],
        "base_skills": [skill0],
        "skill_charges": {},
        "skill_tree_unlocked": [skill0, "guard_basic"],
        "party": [],
        "party_bonds": {},
        "needs": {"hunger": 18, "fatigue": 12, "morale": 72},
        "party_bonus_atk": 0,
        "party_bonus_max_hp": 0,
        "party_bonus_max_mana": 0,
        "bag_cap": 40,
        "base_atk": int(occ.get("atk", 5)) + int(z.get("atk", 0)),
        "base_max_hp": max_hp,
        "base_max_mana": max_mana,
        "base_pressure": int(occ.get("pressure", 10)) + int(z.get("pressure", 0)),
        "gear_tags": [],
        "on_hit_effects": [],
        "area_mastery": mastery,
        "location": start_area,
        "statuses": [],
        "knowledge": {"monsters": {}, "reactions": []},
        "blessings": [],
        "blessing_turns": 0,
        "disciple_of": None,
        "other_players": 0,
        "time_units": 0,
        "action_counts": {"attack": 0, "defend": 0, "explore": 0, "rest": 0},
        "ui_prefs": {
            "show_monster_art_in_combat": False,
            "width": 60,
        },
    }
    # world difficulty modifiers
    mods = dict((reg.worlds.get(world_id) or {}).get("modifiers") or {})
    player["world_modifiers"] = mods
    sm = float(mods.get("start_money_mult", 1.0))
    player["money_world"] = int(int(player["money_world"]) * sm)

    ensure_gear_fields(player)
    ensure_stats(player)
    ensure_personality(player, reg)
    init_progression(player, reg)
    recompute_stats(player, reg)
    _, _, pct = xp_progress(player, reg.levels)
    player["xp_percent"] = round(pct, 1)
    return player


def unlocked_areas(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    lv = int(player.get("level", 1))
    out = []
    for aid, area in reg.areas.items():
        if lv >= int(area.get("unlock_level", 1)):
            out.append(aid)
    return out or list(reg.areas.keys())


def apply_field_regen(player: MutableMapping[str, Any], reg: DataRegistry) -> str:
    area = reg.areas.get(str(player.get("location"))) or {}
    ambient = area.get("ambient") or {}
    hp_r = int(ambient.get("hp_regen", 2))
    mp_r = int(ambient.get("mana_regen", 2))
    old_hp, old_mp = int(player["hp"]), int(player["mana"])
    player["hp"] = min(int(player["max_hp"]), old_hp + hp_r)
    player["mana"] = min(int(player["max_mana"]), old_mp + mp_r)
    # tick statuses via central catalog (DoT + duration)
    from game.domain.status_fx import tick_field_statuses

    tick = tick_field_statuses(player, reg)
    notes = list(tick.notes)
    try:
        from game.domain.narrative import narrate

        for ev in tick.narrative_events:
            notes.extend(
                narrate(
                    reg,
                    str(ev.get("key") or "status_expire"),
                    dmg=int(ev.get("dmg") or 0),
                    status=ev.get("status"),
                    status_name=ev.get("name"),
                )
            )
    except Exception:
        pass
    gained_hp = int(player["hp"]) - old_hp
    gained_mp = int(player["mana"]) - old_mp
    msg = f"ฟื้นฟูตามพื้นที่ HP+{max(0, gained_hp)} MP+{max(0, gained_mp)}"
    if notes:
        flat = []
        for n in notes:
            flat.append(n.strip() if isinstance(n, str) else str(n))
        # dedupe while preserving order
        seen = set()
        uniq = []
        for n in flat:
            if n and n not in seen:
                seen.add(n)
                uniq.append(n)
        msg += " | " + "; ".join(uniq)
    return msg

"""Area boss helpers — multi-phase bosses."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, Optional, Tuple

from game.data_load.registry import DataRegistry


def area_boss_info(reg: DataRegistry, area_id: str) -> Optional[Dict[str, Any]]:
    area = reg.areas.get(area_id) or {}
    bid = area.get("boss_id")
    if not bid or bid not in reg.monsters:
        return None
    mon = dict(reg.monsters[bid])
    return {
        "id": bid,
        "name": mon.get("name", bid),
        "unlock_level": int(area.get("boss_unlock_level", mon.get("level_min", 1))),
        "template": mon,
    }


def spawn_boss(reg: DataRegistry, area_id: str, rng: random.Random) -> Optional[Dict[str, Any]]:
    info = area_boss_info(reg, area_id)
    if not info:
        return None
    base = info["template"]
    mlevel = int(base.get("level_min", 10))
    phases = int(base.get("phases", 3))
    phases = max(1, min(5, phases))
    hp = int(base.get("hp_base", 200)) + rng.randint(0, 30)
    # multi-phase: more total HP
    hp = int(hp * (1.0 + 0.15 * (phases - 1)))
    atk = int(base.get("atk_base", 20))
    elements = list(base.get("elements") or ["physical"])
    profiles = _phase_profiles(1, atk, elements)
    mon = {
        "id": info["id"],
        "name": info["name"],
        "base_name": info["name"],
        "level": mlevel,
        "hp": hp,
        "max_hp": hp,
        "atk": atk,
        "elements": elements,
        "base_elements": elements[:],
        "xp_mult": float(base.get("xp_mult", 3.0)),
        "attack_profiles": profiles,
        "statuses": [],
        "boss": True,
        "phase": 1,
        "max_phases": phases,
        "mechanic": base.get("mechanic"),
        "reflect_pct": 0.0,
        "drain_pct": 0.0,
        "extra_hits": 1,
        "phase_hp_frac": [1.0 - i / phases for i in range(1, phases)],
        "never_flee": True,
        "intel_tier": int(base.get("intel_tier") or 3),
    }
    # D1–D2: boss drop tables + bound cards must reach victory loot
    if base.get("drops") is not None:
        mon["drops"] = list(base.get("drops") or [])
    if base.get("card_id"):
        mon["card_id"] = str(base.get("card_id"))
    if base.get("card_rate"):
        mon["card_rate"] = base.get("card_rate")
    try:
        from game.domain.monster_ai import attach_monster_intel_fields

        attach_monster_intel_fields(mon, base)
        mon["never_flee"] = True
        mon["boss"] = True
    except Exception:
        mon["intel_tier"] = 3
        mon["never_flee"] = True
    try:
        from game.domain.rarity import apply_rarity_to_enemy, roll_enemy_rarity

        area = reg.areas.get(area_id) or {}
        area_tier = int(area.get("world_tier") or area.get("tier") or 2)
        rid = base.get("rarity") or roll_enemy_rarity(
            reg, rng, boss=True, area_tier=area_tier
        )
        mon = apply_rarity_to_enemy(mon, reg, str(rid))
        mon["boss"] = True  # preserve after copy
        mon["never_flee"] = True
        if base.get("drops") is not None:
            mon["drops"] = list(base.get("drops") or [])
        if base.get("card_id"):
            mon["card_id"] = str(base.get("card_id"))
        if base.get("card_rate"):
            mon["card_rate"] = base.get("card_rate")
        try:
            from game.domain.monster_ai import attach_monster_intel_fields

            attach_monster_intel_fields(mon, base)
            mon["never_flee"] = True
            mon["boss"] = True
        except Exception:
            mon["intel_tier"] = int(mon.get("intel_tier") or 3)
    except Exception:
        mon["rarity"] = "rare"
    return mon


def _phase_profiles(phase: int, atk: int, elements: List[str]) -> List[Dict[str, Any]]:
    power = atk + (phase - 1) * 3
    names = {
        1: ("บอสทดสอบแนวรุก!", "พลังระลอกแรก"),
        2: ("เกราะแตก — บอสเดือดดาล!", "ระลอกสอง: ธาตุพุ่ง"),
        3: ("ร่างที่แท้จริงเผยออก!", "ระลอกสุดท้าย: ไม่มีการปรานี"),
        4: ("มิติบิดเบี้ยว!", "เหนือขีดจำกัด"),
        5: ("จุดจบของพื้นที่นี้!", "apocalypse"),
    }
    t1, t2 = names.get(phase, ("บอสโจมตี!", "พลังสูง"))
    return [
        {
            "id": f"p{phase}_a",
            "tags": elements[:1] or ["physical"],
            "telegraph": t1,
            "power": power + 4,
        },
        {
            "id": f"p{phase}_b",
            "tags": elements,
            "telegraph": t2,
            "power": power + 2,
        },
    ]


def check_phase_transition(
    mon: Dict[str, Any],
    rng: random.Random,
) -> Optional[str]:
    """
    If boss HP crossed into next phase, mutate mon and return announcement.
    """
    if not mon.get("boss"):
        return None
    phase = int(mon.get("phase", 1))
    max_p = int(mon.get("max_phases", 1))
    if phase >= max_p:
        return None
    max_hp = max(1, int(mon.get("max_hp", 1)))
    ratio = float(mon.get("hp", 0)) / max_hp
    # enter phase 2 when below (1 - 1/max_phases), etc.
    # phase N active when ratio <= 1 - (N-1)/max_phases ... simpler:
    # threshold to enter phase+1: 1 - phase/max_phases
    threshold = 1.0 - (phase / max_p)
    if ratio > threshold:
        return None

    mon["phase"] = phase + 1
    mon["statuses"] = []  # break CC
    # partial second wind
    heal = int(max_hp * 0.12)
    mon["hp"] = min(max_hp, int(mon["hp"]) + heal)
    # escalate elements
    base_el = list(mon.get("base_elements") or mon.get("elements") or ["physical"])
    extra = {
        2: ["fire", "shadow"],
        3: ["lightning", "arcane"],
        4: ["ice", "holy"],
        5: ["shadow", "fire", "lightning"],
    }.get(mon["phase"], ["physical"])
    new_el = list(dict.fromkeys(base_el + extra))
    mon["elements"] = new_el
    mon["atk"] = int(mon.get("atk", 10)) + 3
    mon["attack_profiles"] = _phase_profiles(mon["phase"], int(mon["atk"]), new_el)
    # unique mechanics per boss id
    mech = str(mon.get("mechanic") or "")
    extra = ""
    if mech == "reflect" or mon.get("id") == "boss_prism_sovereign":
        mon["reflect_pct"] = 0.15 + 0.05 * mon["phase"]
        extra = f" · สะท้อนดาเมจ {int(mon['reflect_pct']*100)}%"
    elif mech == "drain" or mon.get("id") == "boss_void_herald":
        mon["drain_pct"] = 0.2
        extra = " · ดูดเลือดเมื่อโจมตี"
    elif mech == "multi_head" or mon.get("id") == "boss_mist_hydra":
        mon["extra_hits"] = mon["phase"]
        extra = f" · โจมตีซ้ำ {mon['extra_hits']} ครั้ง/เทิร์น"
    else:
        mon["reflect_pct"] = 0.0
        mon["drain_pct"] = 0.0
        mon["extra_hits"] = 1
    return (
        f"⚡ บอสเข้าเฟส {mon['phase']}/{max_p}! "
        f"ธาตุเปลี่ยน · โจมตีแรงขึ้น · ฟื้น {heal} HP · สถานะถูกล้าง{extra}"
    )


def can_challenge_boss(player: Mapping[str, Any], reg: DataRegistry, area_id: str) -> tuple:
    info = area_boss_info(reg, area_id)
    if not info:
        return False, "พื้นที่นี้ไม่มีบอส"
    lv = int(player.get("level", 1))
    need = info["unlock_level"]
    if lv < need:
        return False, f"ต้องการเลเวล {need} (ตอนนี้ {lv})"
    return True, info["name"]

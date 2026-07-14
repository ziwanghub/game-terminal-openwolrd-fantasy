"""
Unit claim (1 per world per unit_id) + mastery curve.
Mastery low → unit skill weak; high → stronger + combo length bonus.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.config import SAVES_DIR
from game.data_load.registry import DataRegistry


def claims_path(world_id: str) -> Path:
    d = SAVES_DIR / str(world_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / "unit_claims.json"


def load_claims(world_id: str) -> Dict[str, Any]:
    path = claims_path(world_id)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_claims(world_id: str, claims: Mapping[str, Any]) -> None:
    path = claims_path(world_id)
    path.write_text(json.dumps(dict(claims), ensure_ascii=False, indent=2), encoding="utf-8")


def is_unit_claimed(world_id: str, unit_id: str, except_player_id: Optional[str] = None) -> bool:
    claims = load_claims(world_id)
    owner = claims.get(unit_id)
    if not owner:
        return False
    if except_player_id and str(owner.get("player_id")) == str(except_player_id):
        return False
    return True


def claim_unit(world_id: str, unit_id: str, player: Mapping[str, Any]) -> bool:
    claims = load_claims(world_id)
    pid = str(player.get("id") or "")
    if unit_id in claims and str(claims[unit_id].get("player_id")) != pid:
        return False
    claims[unit_id] = {
        "player_id": pid,
        "player_name": player.get("name"),
    }
    save_claims(world_id, claims)
    return True


def ensure_unit_mastery(player: MutableMapping[str, Any]) -> None:
    player.setdefault("unit_mastery", 0)
    player.setdefault("unit_mastery_xp", 0)


def mastery_power_mult(mastery: int) -> float:
    """Level 0 weak … 5 strong."""
    table = [0.55, 0.70, 0.85, 1.0, 1.12, 1.25]
    m = max(0, min(5, int(mastery)))
    return table[m]


def mastery_mana_mult(mastery: int) -> float:
    """Low mastery = unit skill more expensive."""
    table = [1.35, 1.2, 1.1, 1.0, 0.95, 0.9]
    m = max(0, min(5, int(mastery)))
    return table[m]


def soft_mastery_label(mastery: int) -> str:
    labels = ["ยังเงียบ", "กระซิบ", "ตื่นบางส่วน", "ประสาน", "มั่นคง", "ตื่นเต็ม"]
    m = max(0, min(5, int(mastery)))
    return labels[m]


def gain_unit_mastery_xp(
    player: MutableMapping[str, Any],
    amount: int = 1,
    reason: str = "",
) -> List[str]:
    """Hidden XP toward mastery ranks."""
    if not player.get("unit_class_id"):
        return []
    ensure_unit_mastery(player)
    notes: List[str] = []
    player["unit_mastery_xp"] = int(player.get("unit_mastery_xp") or 0) + max(0, amount)
    # thresholds: 5, 15, 30, 50, 80
    thresholds = [5, 15, 30, 50, 80]
    cur = int(player.get("unit_mastery") or 0)
    xp = int(player["unit_mastery_xp"])
    while cur < 5 and xp >= thresholds[cur]:
        cur += 1
        player["unit_mastery"] = cur
        notes.append(f"◆ Unit …{soft_mastery_label(cur)} (รู้สึกถึงการประสานลึกขึ้น)")
    return notes


def try_unit_unlock_with_claim(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """Wrap unit unlock with world claim exclusivity + start mastery 0."""
    if player.get("unit_class_id"):
        return []
    from game.domain.progression import ensure_progression, recompute_powers

    units = getattr(reg, "unit_classes", None) or {}
    if not units:
        return []
    ensure_progression(player, reg)
    world_id = str(player.get("world_id") or "default")
    st = player.get("stats") or {}
    alloc = player.get("stats_alloc") or {}
    oid = str(player.get("occupation_id") or "")
    lib_n = len(player.get("library_entries_read") or [])
    rng = random.Random(int(player.get("latent_seed", 1)) + int(player.get("level", 1)))
    pid = str(player.get("id") or "")

    candidates = []
    for uid, u in units.items():
        if is_unit_claimed(world_id, uid, except_player_id=pid):
            continue
        un = u.get("unlock") or {}
        if int(player.get("level", 1)) < int(un.get("min_level", 99)):
            continue
        allowed = un.get("occupation_ids") or []
        if allowed and oid not in allowed:
            continue
        if int(alloc.get("crit", 0)) < int(un.get("min_stat_crit", 0)):
            continue
        if int(alloc.get("defense", 0)) < int(un.get("min_stat_defense", 0)):
            continue
        if int(alloc.get("magic", 0)) < int(un.get("min_stat_magic", 0)):
            continue
        if int(st.get("boss_kills", 0)) < int(un.get("min_boss_kills", 0)):
            continue
        combos = int(st.get("combos", 0)) or int((player.get("action_counts") or {}).get("attack", 0)) // 3
        if combos < int(un.get("min_combos", 0)):
            continue
        if lib_n < int(un.get("require_library_entries", 0)):
            continue
        chance = float(un.get("chance", 0.25))
        if rng.random() <= chance:
            candidates.append(uid)

    if not candidates:
        return []
    uid = rng.choice(candidates)
    if not claim_unit(world_id, uid, player):
        return ["…เงา Unit ถูกผู้อื่นครอบครองในโลกนี้แล้ว"]
    u = units[uid]
    player["unit_class_id"] = uid
    player["unit_class_name"] = u.get("name", uid)
    sk = u.get("exclusive_skill")
    player["unit_skill"] = sk
    ensure_unit_mastery(player)
    player["unit_mastery"] = 0
    player["unit_mastery_xp"] = 0
    if sk and sk in reg.skills:
        skills = list(player.get("skills") or [])
        if sk not in skills:
            skills.append(sk)
            player["skills"] = skills
        base = list(player.get("base_skills") or [])
        if sk not in base:
            base.append(sk)
            player["base_skills"] = base
    recompute_powers(player, reg)
    return [
        f"◆◆◆ Unit ปลุกขึ้น: {u.get('name')} ◆◆◆",
        f"สถานะ: {soft_mastery_label(0)} — ใช้ไม่เป็นจะอ่อน (ต้องประยุกต์)",
        "Unit ชนิดนี้มีเจ้าของได้เพียงหนึ่งในโลกนี้",
    ]


def apply_unit_skill_scaling(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
    power: int,
    mana: int,
) -> Tuple[int, int]:
    """Scale unit_only skills by mastery."""
    if not skill.get("unit_only"):
        return power, mana
    if not player.get("unit_class_id"):
        return power, mana
    m = int(player.get("unit_mastery") or 0)
    p = int(round(power * mastery_power_mult(m)))
    c = int(round(mana * mastery_mana_mult(m)))
    return max(1, p), max(0, c)

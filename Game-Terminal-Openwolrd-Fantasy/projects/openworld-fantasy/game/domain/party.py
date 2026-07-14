"""
Party system — max 3 companions (players or spirits/beasts/gods...).
Recruitment requires hidden consent; calling power has per-use costs.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry


MAX_PARTY = 3


def _cfg(reg: DataRegistry) -> Dict[str, Any]:
    return dict(getattr(reg, "party", None) or {})


def ensure_party(player: MutableMapping[str, Any]) -> List[Dict[str, Any]]:
    party = list(player.get("party") or [])
    player["party"] = party[:MAX_PARTY]
    player.setdefault("party_bonds", {})  # member_id -> bond int
    player.setdefault("party_calls", 0)
    return player["party"]


def max_party_size(reg: DataRegistry) -> int:
    return int(_cfg(reg).get("max_party_size") or MAX_PARTY)


def party_size(player: Mapping[str, Any]) -> int:
    return len(player.get("party") or [])


def kind_label(reg: DataRegistry, kind_id: str) -> str:
    for k in _cfg(reg).get("kinds") or []:
        if str(k.get("id")) == kind_id:
            return str(k.get("name") or kind_id)
    return kind_id


def template_by_id(reg: DataRegistry, tid: str) -> Optional[Dict[str, Any]]:
    for t in _cfg(reg).get("templates") or []:
        if str(t.get("id")) == tid:
            return dict(t)
    return None


def format_party_panel(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_party(player)  # type: ignore
    mx = max_party_size(reg)
    lines = [f"── ปาร์ตี้ ({party_size(player)}/{mx}) ──"]
    party = list(player.get("party") or [])
    if not party:
        lines.append("  ว่าง — ต้องได้รับการยอมรับจึงร่วมทีมได้ (วิธีได้มาไม่บอก)")
        lines.append("  เรียกใช้พลังปาร์ตี้มีเงื่อนไขแต่ละครั้ง")
        return lines
    bonds = player.get("party_bonds") or {}
    for i, m in enumerate(party, 1):
        kind = kind_label(reg, str(m.get("kind") or "other"))
        name = m.get("name") or m.get("id")
        bond = int(bonds.get(str(m.get("id")), m.get("bond", 0)) or 0)
        soft = "สนิท" if bond >= 5 else ("คุ้น" if bond >= 2 else "ใหม่")
        rlab = m.get("rarity_label") or m.get("rarity") or ""
        rbit = f" · {rlab}" if rlab else ""
        lines.append(f"  {i}. {name} · {kind}{rbit} · ความผูกพัน:{soft}")
        if m.get("flavor"):
            lines.append(f"     “{m.get('flavor')}”")
    lines.append("  (ตัวเลขพลังสมาชิกซ่อน · เรียกใช้ตอนไฟต์มีต้นทุน · ช่วยโจมตีอัตโนมัติได้)")
    if player.get("unit_class_id"):
        from game.domain.unit_system import soft_mastery_label

        lines.append(
            f"  Unit: {player.get('unit_class_name')} · "
            f"{soft_mastery_label(int(player.get('unit_mastery') or 0))}"
        )
    return lines


def _has_slot(player: Mapping[str, Any], reg: DataRegistry) -> bool:
    return party_size(player) < max_party_size(reg)


def _already_in(player: Mapping[str, Any], mid: str) -> bool:
    return any(str(m.get("id")) == mid for m in (player.get("party") or []))


def can_recruit_template(
    player: Mapping[str, Any],
    reg: DataRegistry,
    template: Mapping[str, Any],
    *,
    affinity: float = 0.5,
) -> Tuple[bool, str]:
    """Hidden checks — messages stay vague."""
    if not _has_slot(player, reg):
        return False, "ทีมเต็มแล้ว (สูงสุด 3)"
    tid = str(template.get("id"))
    if _already_in(player, tid):
        return False, "อยู่ร่วมทางอยู่แล้ว"
    if int(player.get("level", 1)) < int(template.get("min_level") or 1):
        return False, "ยังไม่พร้อมเดินด้วยกัน"
    need = float(template.get("affinity_need") or 0)
    if affinity < need:
        return False, "มันยังไม่ยอมรับคุณ"
    area = str(player.get("location") or "")
    req_area = template.get("require_area")
    if req_area and area != req_area:
        return False, "ที่นี่ไม่ใช่ที่ของมัน"
    st = player.get("stats") or {}
    if int(st.get("boss_kills", 0)) < int(template.get("require_boss_kills") or 0):
        return False, "ยังขาดบางอย่างที่มันมองหา"
    if int(st.get("deaths", 0)) < int(template.get("require_deaths") or 0):
        return False, "เส้นทางของคุณยังตื้นเกินไป"
    lib = len(player.get("library_entries_read") or [])
    if lib < int(template.get("require_library") or 0):
        return False, "ความรู้ยังไม่พอให้มันเชื่อ"
    if int(player.get("money_heaven", 0)) < int(template.get("require_money_heaven") or 0):
        return False, "ขาดของจากสวรรค์"
    if int(player.get("money_hell", 0)) < int(template.get("require_money_hell") or 0):
        return False, "ขาดของจากนรก"
    return True, "ok"


def add_member(player: MutableMapping[str, Any], member: Dict[str, Any], reg: DataRegistry) -> str:
    ensure_party(player)
    if not _has_slot(player, reg):
        return "ปาร์ตี้เต็ม (สูงสุด 3)"
    mid = str(member.get("id") or "")
    if not mid or _already_in(player, mid):
        return "มีสมาชิกนี้อยู่แล้ว"
    party = list(player["party"])
    party.append(member)
    player["party"] = party
    bonds = dict(player.get("party_bonds") or {})
    bonds[mid] = int(member.get("bond") or 1)
    player["party_bonds"] = bonds
    return f"✦ {member.get('name')} ยอมร่วมทางแล้ว ({kind_label(reg, str(member.get('kind')))})"


def remove_member(player: MutableMapping[str, Any], index: int) -> str:
    ensure_party(player)
    party = list(player["party"])
    if index < 0 or index >= len(party):
        return "ไม่มีสมาชิกช่องนั้น"
    m = party.pop(index)
    player["party"] = party
    return f"{m.get('name')} แยกทางไป..."


def member_from_template(
    template: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
    *,
    rarity: Optional[str] = None,
) -> Dict[str, Any]:
    from game.domain.rarity import rarity_label, roll_rarity, scale_stat

    kind = str(template.get("kind") or "other")
    rid = rarity
    if not rid:
        if template.get("rarity"):
            rid = str(template["rarity"])
        elif reg is not None:
            rng = rng or random.Random()
            # higher kinds can roll higher max
            max_rank = {
                "heaven_god": 8,
                "hell_god": 8,
                "heaven_beast": 6,
                "hell_beast": 6,
                "spirit": 5,
                "beast": 5,
                "other": 6,
            }.get(kind, 5)
            rid = roll_rarity(reg, rng, kind=kind, pool="recruit", max_rank=max_rank)
        else:
            rid = "common"
    base_atk = int(template.get("bonus_atk") or 0)
    base_hp = int(template.get("bonus_max_hp") or 0)
    base_mp = int(template.get("bonus_max_mana") or 0)
    return {
        "id": str(template.get("id")),
        "name": template.get("name"),
        "kind": kind,
        "source": "template",
        "rarity": rid,
        "rarity_label": rarity_label(reg, rid) if reg else rid,
        "bonus_atk": scale_stat(base_atk, rid, reg),
        "bonus_max_hp": scale_stat(base_hp, rid, reg),
        "bonus_max_mana": scale_stat(base_mp, rid, reg),
        "call_mana": int(template.get("call_mana") or 4),
        "call_world": int(template.get("call_world") or 0),
        "call_heaven": int(template.get("call_heaven") or 0),
        "call_hell": int(template.get("call_hell") or 0),
        "flavor": template.get("flavor") or "",
        "bond": 1,
    }


def member_from_player_echo(
    other: Mapping[str, Any],
    affinity: float,
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Hire another world's player — stats scaled soft, never show raw numbers."""
    from game.domain.rarity import rarity_label, roll_rarity, scale_stat

    atk = max(1, int(other.get("bonus_atk") or 5) // 4)
    hp = max(5, int(other.get("max_hp") or 80) // 12)
    mp = max(2, int(other.get("max_mana") or 40) // 10)
    rid = "common"
    if reg is not None:
        rng = rng or random.Random()
        rid = roll_rarity(reg, rng, kind="player", pool="recruit", max_rank=5)
    atk = scale_stat(atk + (1 if affinity > 0.4 else 0), rid, reg, floor=1)
    hp = scale_stat(hp, rid, reg, floor=1)
    mp = scale_stat(mp, rid, reg, floor=1)
    return {
        "id": f"player:{other.get('id') or other.get('name')}",
        "name": other.get("name") or "ผู้พเนจร",
        "kind": "player",
        "source": "player_echo",
        "ref_player_id": other.get("id"),
        "rarity": rid,
        "rarity_label": rarity_label(reg, rid) if reg else rid,
        "bonus_atk": atk,
        "bonus_max_hp": hp,
        "bonus_max_mana": mp,
        "call_mana": 5 + max(0, 3 - int(affinity * 5)),
        "call_world": 10 if affinity < 0.3 else 0,
        "call_heaven": 0,
        "call_hell": 0,
        "flavor": f"สาย {(other.get('occ_path') or other.get('occupation') or '???')}",
        "bond": 1 if affinity < 0.5 else 2,
        "affinity_at_hire": round(affinity, 3),
    }


def try_consent_player_hire(
    player: Mapping[str, Any],
    other: Mapping[str, Any],
    reg: DataRegistry,
    affinity: float,
    rng: random.Random,
) -> Tuple[bool, str]:
    """Hidden consent roll — need acceptance, not automatic."""
    if not _has_slot(player, reg):
        return False, "ทีมเต็ม — เขาพยักหน้าแล้วจาก"
    if _already_in(player, f"player:{other.get('id')}"):
        return False, "ร่วมทางอยู่แล้ว"
    base = float(_cfg(reg).get("player_hire_base_chance") or 0.35)
    # better affinity → easier consent; foe path hard
    chance = base + max(-0.25, min(0.45, affinity * 0.4))
    if affinity < -0.2:
        return False, "เขาปฏิเสธเด็ดขาด"
    if rng.random() > chance:
        return False, "เขายังไม่ยอมรับการร่วมทีม... (ต้องลองสร้างความสัมพันธ์)"
    return True, "ok"


def try_recruit_template_offer(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    affinity: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Maybe offer a template companion after explore/sight — conditions hidden."""
    if not _has_slot(player, reg):
        return None
    templates = list(_cfg(reg).get("templates") or [])
    if not templates:
        return None
    rng.shuffle(templates)
    aff = float(affinity if affinity is not None else 0.3 + rng.random() * 0.4)
    for t in templates:
        ok, _ = can_recruit_template(player, reg, t, affinity=aff)
        if ok and rng.random() < 0.45:
            return dict(t)
    return None


def party_passive_bonuses(player: Mapping[str, Any]) -> Dict[str, int]:
    """Always-on soft bonuses from party (smaller than call)."""
    atk = hp = mp = 0
    for m in player.get("party") or []:
        atk += max(0, int(m.get("bonus_atk") or 0) // 2)
        hp += max(0, int(m.get("bonus_max_hp") or 0) // 3)
        mp += max(0, int(m.get("bonus_max_mana") or 0) // 3)
    return {"atk": atk, "max_hp": hp, "max_mana": mp}


def apply_party_passives_to_player(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    """Store party passive deltas for recompute (non-destructive base)."""
    ensure_party(player)
    b = party_passive_bonuses(player)
    player["party_bonus_atk"] = b["atk"]
    player["party_bonus_max_hp"] = b["max_hp"]
    player["party_bonus_max_mana"] = b["max_mana"]


def call_party_power(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    member_index: int,
) -> Tuple[bool, str, Dict[str, int]]:
    """
    Activate one member's full bonus for this fight burst.
    Returns (ok, message, bonuses_applied).
    Conditions/costs per member — player discovers by trying.
    """
    ensure_party(player)
    party = list(player.get("party") or [])
    if member_index < 0 or member_index >= len(party):
        return False, "ไม่มีสมาชิก", {}
    m = party[member_index]
    cm = int(m.get("call_mana") or _cfg(reg).get("call_base_mana") or 4)
    cw = int(m.get("call_world") or 0)
    ch = int(m.get("call_heaven") or 0)
    cl = int(m.get("call_hell") or 0)
    if int(player.get("mana", 0)) < cm:
        return False, "มานาไม่พอสำหรับเรียกใช้", {}
    if int(player.get("money_world", 0)) < cw:
        return False, "เงื่อนไขเรียกใช้ยังไม่ครบ (ทรัพยากรโลก?)", {}
    if int(player.get("money_heaven", 0)) < ch:
        return False, "เงื่อนไขเรียกใช้ยังไม่ครบ (สวรรค์?)", {}
    if int(player.get("money_hell", 0)) < cl:
        return False, "เงื่อนไขเรียกใช้ยังไม่ครบ (นรก?)", {}

    player["mana"] = int(player["mana"]) - cm
    if cw:
        player["money_world"] = int(player.get("money_world", 0)) - cw
    if ch:
        player["money_heaven"] = int(player.get("money_heaven", 0)) - ch
    if cl:
        player["money_hell"] = int(player.get("money_hell", 0)) - cl

    bonds = dict(player.get("party_bonds") or {})
    mid = str(m.get("id"))
    bonds[mid] = int(bonds.get(mid, 0)) + 1
    player["party_bonds"] = bonds
    player["party_calls"] = int(player.get("party_calls", 0)) + 1

    bonuses = {
        "atk": int(m.get("bonus_atk") or 0),
        "max_hp": int(m.get("bonus_max_hp") or 0),
        "max_mana": int(m.get("bonus_max_mana") or 0),
    }
    # temporary fight buff
    player["bonus_atk"] = int(player.get("bonus_atk", 0)) + bonuses["atk"]
    player["max_hp"] = int(player.get("max_hp", 0)) + bonuses["max_hp"]
    player["hp"] = min(int(player["max_hp"]), int(player.get("hp", 0)) + bonuses["max_hp"] // 2)
    player["max_mana"] = int(player.get("max_mana", 0)) + bonuses["max_mana"]
    player["mana"] = min(int(player["max_mana"]), int(player.get("mana", 0)) + bonuses["max_mana"] // 3)
    # track for end-of-fight cleanup optional
    pend = list(player.get("party_call_active") or [])
    pend.append({"id": mid, **bonuses})
    player["party_call_active"] = pend

    name = m.get("name") or mid
    return True, f"✧ เรียก「{name}」ช่วยแนวรบ! (ต้นทุนถูกหักตามเงื่อนไขซ่อน)", bonuses


def party_assist_damage(
    player: Mapping[str, Any],
    mon: MutableMapping[str, Any],
    rng: random.Random,
    reg: Optional[Any] = None,
) -> List[str]:
    """Backward-compatible alias → party_member_turns (full soft AI). """
    return party_member_turns(player, mon, rng, reg)  # type: ignore[arg-type]


def party_member_turns(
    player: MutableMapping[str, Any],
    mon: MutableMapping[str, Any],
    rng: random.Random,
    reg: Optional[Any] = None,
) -> List[str]:
    """
    Soft full party turns after the player acts.
    Each member may: โจมตี · รักษา · บัฟเบา — เลือกตาม kind + สถานการณ์ (ไม่โชว์สูตร).
    """
    notes: List[str] = []
    party = list(player.get("party") or [])
    if not party or int(mon.get("hp", 0)) <= 0:
        return notes
    bonds = player.get("party_bonds") or {}
    notes.append("  ── เทิร์นปาร์ตี้ ──")
    acted_any = False
    for m in party:
        if int(mon.get("hp", 0)) <= 0:
            break
        mid = str(m.get("id"))
        bond = int(bonds.get(mid, m.get("bond", 1)) or 1)
        # higher bond → almost always acts
        chance = 0.55 + min(0.40, bond * 0.06)
        if rng.random() > chance:
            continue
        acted_any = True
        name = m.get("name") or mid
        kind = str(m.get("kind") or "")
        base = max(1, int(m.get("bonus_atk") or 2))
        hp_ratio = int(player.get("hp") or 0) / max(1, int(player.get("max_hp") or 1))
        mon_ratio = int(mon.get("hp") or 0) / max(1, int(mon.get("max_hp") or 1))
        # choose action soft — situational (player low · finish elite · kind)
        action = "attack"
        if hp_ratio < 0.30:
            # emergency heal bias for any kind
            if kind in ("spirit", "heaven_god", "heaven_beast", "player") or rng.random() < 0.55:
                action = "heal"
            else:
                action = "attack"
        elif kind in ("spirit", "heaven_god", "heaven_beast") and hp_ratio < 0.45:
            action = "heal"
        elif kind in ("spirit",) and rng.random() < 0.35:
            action = "heal"
        elif mon_ratio <= 0.22 and (mon.get("elite") or mon.get("boss") or mon_ratio <= 0.15):
            # finish wounded high-value foe
            action = "attack"
        elif kind in ("player", "beast", "hell_beast", "hell_god") or rng.random() < 0.7:
            action = "attack"
        else:
            action = "buff"
        # finishing blow slightly stronger when mon is nearly done
        finish_mult = 1.0
        if action == "attack" and mon_ratio <= 0.25:
            finish_mult = 1.12 + (0.08 if mon.get("elite") or mon.get("boss") else 0.0)

        if action == "heal":
            heal = max(2, int(round(base * (1.2 + bond * 0.1) + rng.randint(1, 4))))
            player["hp"] = min(int(player.get("max_hp") or heal), int(player.get("hp") or 0) + heal)
            notes.append(f"  › {name} รักษาเบา → HP +{heal}")
        elif action == "buff":
            player["bonus_atk"] = int(player.get("bonus_atk") or 0) + max(1, base // 3)
            pend = list(player.get("party_call_active") or [])
            pend.append({"id": f"softbuff:{mid}", "atk": max(1, base // 3), "max_hp": 0, "max_mana": 0})
            player["party_call_active"] = pend
            notes.append(f"  › {name} เสริมพลังแนวรบ (ชั่วคราว)")
        else:
            kmult = {
                "player": 1.15,
                "beast": 1.2,
                "hell_beast": 1.25,
                "heaven_beast": 1.1,
                "heaven_god": 1.35,
                "hell_god": 1.4,
                "spirit": 0.95,
            }.get(kind, 1.0)
            dmg = max(
                1,
                int(round(base * kmult * finish_mult * (0.85 + rng.random() * 0.55))),
            )
            mon["hp"] = int(mon.get("hp", 0)) - dmg
            try:
                from game.domain.narrative import narrate

                flavor = narrate(reg, "party_assist", rng, name=name, dmg=dmg)
                if flavor:
                    notes.extend(flavor)
                else:
                    notes.append(f"  › {name} โจมตี → {dmg}")
            except Exception:
                notes.append(f"  › {name} โจมตี → {dmg}")
            if int(mon.get("hp", 0)) <= 0:
                notes.append(f"  › {name} ปิดงาน!")
                break
        # soft bond growth rare
        if rng.random() < 0.12:
            bonds = dict(player.get("party_bonds") or {})
            bonds[mid] = int(bonds.get(mid, bond)) + 1
            player["party_bonds"] = bonds
    if not acted_any:
        notes.append("  › สมาชิกยังรอดูจังหวะ…")
    return notes


def clear_party_call_buffs(player: MutableMapping[str, Any]) -> None:
    """Remove temporary call bonuses after combat (best-effort)."""
    active = list(player.get("party_call_active") or [])
    if not active:
        return
    for b in active:
        player["bonus_atk"] = max(0, int(player.get("bonus_atk", 0)) - int(b.get("atk") or 0))
        # max_hp/mana reductions careful of current hp
        player["max_hp"] = max(10, int(player.get("max_hp", 10)) - int(b.get("max_hp") or 0))
        player["hp"] = min(int(player["hp"]), int(player["max_hp"]))
        player["max_mana"] = max(0, int(player.get("max_mana", 0)) - int(b.get("max_mana") or 0))
        player["mana"] = min(int(player.get("mana", 0)), int(player["max_mana"]))
    player["party_call_active"] = []


def roll_recruit_sight(player: Mapping[str, Any], reg: DataRegistry, rng: random.Random) -> bool:
    ch = float(_cfg(reg).get("recruit_sight_chance") or 0.12)
    return rng.random() < ch

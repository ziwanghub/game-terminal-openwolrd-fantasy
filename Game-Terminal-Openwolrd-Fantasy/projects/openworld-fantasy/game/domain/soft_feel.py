"""
Soft observation feedback — no %, no formulas.
Players feel latent gear, upgrade, and secret-class affinity through short lines.
"""
from __future__ import annotations

from typing import Any, List, Mapping, MutableMapping, Optional, Sequence

from game.data_load.registry import DataRegistry  # noqa: F401 — used in signatures


def soft_equip_feel(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    slot: str = "",
    item_id: str = "",
) -> List[str]:
    """After equipping a piece — primary shown elsewhere; here only soft latent feel."""
    notes: List[str] = []
    it = reg.items.get(item_id) or {}
    from game.domain.equipment import item_grip, normalize_slot
    from game.domain.rarity import equip_rarity_for_slot, scaled_item_stats

    ns = normalize_slot(slot or str(it.get("slot") or "main_hand"))
    rid = equip_rarity_for_slot(player, ns)
    up = int((player.get("upgrade_levels") or {}).get(ns, 0))
    st = scaled_item_stats(it, rid, reg, upgrade_level=up, slot=ns)
    grip = item_grip(it)

    # armor / shield endurance latent — standard path bands
    if ns in ("body", "head", "legs", "feet") or grip == "shield" or st.get("def") or st.get("mdef"):
        lat = float(st.get("latent_hp_pct") or 0) + float(st.get("latent_tough") or 0) * 0.02
        if lat >= 0.055:
            notes.append("「เข้าทาง」เกราะอุ้มร่างแน่น (เลือดรวมอาจหนา — สังเกตเอง)")
        elif lat > 0.02:
            notes.append("「พอใช้」เกราะอุ้มอะไรบางอย่างแผ่วๆ")
        elif lat > 0:
            notes.append("「พอใช้」เกราะอุ้มแผ่วมาก…")
        if float(st.get("latent_status_resist") or 0) > 0.01:
            notes.append("…รู้สึกต้านสถานะดีขึ้นนิด (ไม่รู้ชัด)")

    # weapon offense latent
    if int(st.get("atk") or 0) > 0 and ns in ("main_hand", "off_hand", "weapon"):
        oa = float(st.get("latent_atk_pct") or 0)
        oc = float(st.get("latent_crit") or 0)
        if oa >= 0.028 or oc >= 1.1:
            notes.append("「เข้าทาง」คมแฝงแน่น (สังเกตแรง/คริในไฟต์)")
        elif oa > 0 or oc > 0:
            notes.append("「พอใช้」คมแฝงบางอย่าง (สังเกตในไฟต์)")

    # loadout stance
    for n in list(player.get("loadout_soft_notes") or [])[:1]:
        if n and n not in notes:
            notes.append(f"「{n}」")

    # secret occupation affinity after gear change
    notes.extend(soft_unit_affinity_feel(player, reg, force=False))
    return notes[:3]


def soft_upgrade_feel(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    slot: str,
    success: bool,
) -> List[str]:
    """After upgrade attempt — success tightens latent; fail is already messaged."""
    if not success:
        return []
    notes: List[str] = []
    eid = (player.get("equip_ids") or {}).get(slot)
    if not eid:
        return []
    it = reg.items.get(eid) or {}
    from game.domain.equipment import normalize_slot
    from game.domain.rarity import equip_rarity_for_slot, scaled_item_stats

    ns = normalize_slot(slot)
    rid = equip_rarity_for_slot(player, ns)
    up = int((player.get("upgrade_levels") or {}).get(ns, 0))
    st = scaled_item_stats(it, rid, reg, upgrade_level=up, slot=ns)
    if st.get("atk"):
        notes.append("「เข้าทาง」คมหลักและคมแฝงแน่นขึ้นเล็กน้อย (สังเกตไฟต์)")
    if st.get("def") or st.get("mdef"):
        notes.append("「เข้าทาง」กันแน่นขึ้น · อึดแฝงอาจตามมา (สังเกตเลือด)")
    if up >= 5:
        notes.append("…พิธีลึกแล้ว — เสี่ยงรอบหน้าสูงขึ้น")
    return notes[:2]


def soft_skill_learn_feel(skill: Mapping[str, Any]) -> str:
    """After learning a tree skill — soft, no spoilers."""
    tier = int(skill.get("tier") or 1)
    slot = str(skill.get("slot") or "combat")
    if tier >= 4:
        return "「เข้าทาง」ท่านี้หนัก — รู้สึกถึงปลายทางสายอาชีพ"
    if tier >= 3:
        if slot == "defense":
            return "「พอใช้」เกราะท่าใหม่ฝังในกล้ามเนื้อ"
        if slot == "support":
            return "「พอใช้」ท่าสนับสนุนเข้าที่"
        return "「เข้าทาง」ท่ากลางสาย — ทางแยกอาชีพชัดขึ้น"
    return "「พอใช้」พื้นฐานแน่นขึ้นนิด"


def soft_unit_affinity_feel(
    player: Mapping[str, Any],
    reg: DataRegistry,
    *,
    force: bool = True,
) -> List[str]:
    """Secret occupation: stat + style resonance soft band."""
    if not player.get("unit_class_id"):
        return []
    sk_id = player.get("unit_skill")
    sk = (reg.skills.get(str(sk_id)) if sk_id else None) or {}
    if not sk.get("unit_only"):
        return []
    from game.domain.unit_system import soft_affinity_feel, unit_effective_mult

    mult = unit_effective_mult(player, sk, reg)
    if not force and 0.5 <= mult <= 1.15:
        return []
    return [soft_affinity_feel(player, sk, reg)]


def soft_unit_combat_feel(
    player: Mapping[str, Any],
    skill: Mapping[str, Any],
    damage: int,
    reg: Optional[DataRegistry] = None,
) -> List[str]:
    """After firing a unit skill — soft path band (เข้าทาง/พอใช้/ผิดทาง)."""
    if not skill.get("unit_only"):
        return []
    from game.domain.unit_system import soft_path_band, unit_effective_mult

    if reg is None:
        try:
            from game.data_load.registry import get_registry

            reg = get_registry()
        except Exception:
            reg = None
    mult = unit_effective_mult(player, skill, reg)
    band = soft_path_band(mult)
    notes: List[str] = []
    if band == "ผิดทาง":
        notes.append("「ผิดทาง」อาชีพลับแทบไม่ตอบ — สไตล์/แต้มยังไม่ตรง")
    elif band == "พอใช้":
        notes.append("「พอใช้」อาชีพลับตอบแผ่ว")
    else:
        if mult >= 1.7 and damage >= 12:
            notes.append("「เข้าทาง」อาชีพลับระเบิดแรงผิดปกติ…")
        elif damage >= 20 or mult >= 1.1:
            notes.append("「เข้าทาง」อาชีพลับสั่นแรง")
        else:
            notes.append("「เข้าทาง」อาชีพลับตอบสนองดี")
    return notes


def soft_level_up_bundle(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    """Extra soft lines after level-up notes (class offer already separate)."""
    out: List[str] = []
    out.extend(soft_unit_affinity_feel(player, reg, force=False))
    return out

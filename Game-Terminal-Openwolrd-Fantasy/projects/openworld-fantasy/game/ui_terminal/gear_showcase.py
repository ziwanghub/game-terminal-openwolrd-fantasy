"""
Rarity-tiered text UI for gear examine (bag → equipment).

Higher ranks use more ornate frames, epithets, and mini-ASCII so pure-text
play still feels premium vs ordinary weapons.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from game.config import UI_WIDTH
from game.data_load.registry import DataRegistry
from game.ui_terminal.layout import display_width, pad_to_width


# Flavor lines by rarity — imagination hooks (not combat formulas)
_EPITHETS: Dict[str, str] = {
    "common": "เหล็กเรียบ — ดาบนักเดินทางทั่วไป คมพอใช้",
    "uncommon": "คมขึ้นเล็กน้อย — ช่างตีที่ใส่ใจเกินราคา",
    "rare": "แสงสะท้อนเย็นชา — ของหายากจากสนามรบ",
    "sacred": "พรจากวิหารจางๆ — ใบมีดสว่างในเงามืด",
    "legendary": "ชื่อก้องในมหากาพย์ — คมที่ตัดชะตา",
    "divine": "อาวุธแห่งสวรรค์ — ลมหายใจเทพสถิตในด้าม",
    "archdivine": "มหาเทพเคยถือ — ความว่างสั่นเมื่อชักออก",
    "mythic": "ก่อนกำเนิดโลก — ปฐมกาลแห่งคมดาบ",
}

# Soft grade label (player-facing "weapon level")
_GRADE_LABEL: Dict[str, str] = {
    "common": "เกรดพื้นฐาน",
    "uncommon": "เกรดดี",
    "rare": "เกรดหายาก",
    "sacred": "เกรดศักดิ์สิทธิ์",
    "legendary": "เกรดตำนาน",
    "divine": "เกรดเทพ",
    "archdivine": "เกรดมหาเทพ",
    "mythic": "เกรดปฐมกาล",
}


def _tier_meta(reg: Optional[DataRegistry], rarity_id: str) -> Dict[str, Any]:
    from game.domain.rarity import tier_by_id

    t = tier_by_id(reg, rarity_id)
    rid = str(t.get("id") or "common")
    return {
        "id": rid,
        "name": str(t.get("name") or rid),
        "rank": int(t.get("rank") or 1),
        "tag": str(t.get("color_tag") or "○"),
        "stat_mult": float(t.get("stat_mult") or 1.0),
    }


def _slot_glyph(slot: str) -> str:
    return {"weapon": "⚔", "armor": "⛨", "accessory": "◆"}.get(slot, "●")


def _sword_art(rank: int) -> List[str]:
    """Mini ASCII silhouette — more strokes as rank rises."""
    if rank <= 1:
        return [
            "      /|",
            "     //|   ← ดาบธรรมดา",
            "    // |",
            "   '---'",
        ]
    if rank == 2:
        return [
            "      /|\\",
            "     //|\\\\  ← คมสองด้าน",
            "    // | \\\\",
            "   '---'  '",
        ]
    if rank == 3:
        return [
            "     * /|\\ *",
            "      //|\\\\     แสงสะท้อน",
            "     // | \\\\",
            "    '---+---'",
        ]
    if rank == 4:
        return [
            "    ★  /|\\  ★",
            "      //|\\\\",
            "   ★ // | \\\\ ★  ศักดิ์สิทธิ์",
            "     '---+---'",
            "       |||",
        ]
    if rank == 5:
        return [
            "   ✦══ /|\\ ══✦",
            "      //|\\\\",
            "  ✦  // | \\\\  ✦   ตำนาน",
            "     '══+══'",
            "       |||",
            "      ═════",
        ]
    if rank == 6:
        return [
            "  ✧░▒ /|\\ ▒░✧",
            "     //|\\\\",
            " ✧  // | \\\\  ✧  เทพ",
            "    '✧═+═✧'",
            "      |||||",
            "   ░░═════░░",
        ]
    if rank == 7:
        return [
            " ✪◉◉ /|\\ ◉◉✪",
            "    //|\\\\",
            "✪  // | \\\\  ✪  มหาเทพ",
            "   '✪═+═✪'",
            "     |||||",
            "  ▓▓═══════▓▓",
            "    · · · ·",
        ]
    # mythic
    return [
        "◈════════════════◈",
        "  ◈  /|\\  ◈   ปฐมกาล",
        "    //|\\\\",
        "◈  // | \\\\  ◈",
        "   '◈═+═◈'",
        "     |||||",
        " ░▒▓█████▓▒░",
        "  · ✦ · ✦ ·",
    ]


def _frame_style(rank: int) -> Dict[str, str]:
    """Border characters by rank band."""
    if rank <= 1:
        return {
            "tl": "┌",
            "tr": "┐",
            "bl": "└",
            "br": "┘",
            "h": "─",
            "v": "│",
            "ml": "├",
            "mr": "┤",
            "corner": "·",
        }
    if rank == 2:
        return {
            "tl": "◇",
            "tr": "◇",
            "bl": "◇",
            "br": "◇",
            "h": "─",
            "v": "│",
            "ml": "├",
            "mr": "┤",
            "corner": "◇",
        }
    if rank == 3:
        return {
            "tl": "◆",
            "tr": "◆",
            "bl": "◆",
            "br": "◆",
            "h": "═",
            "v": "║",
            "ml": "╠",
            "mr": "╣",
            "corner": "◆",
        }
    if rank == 4:
        return {
            "tl": "★",
            "tr": "★",
            "bl": "★",
            "br": "★",
            "h": "═",
            "v": "║",
            "ml": "╠",
            "mr": "╣",
            "corner": "★",
        }
    if rank == 5:
        return {
            "tl": "✦",
            "tr": "✦",
            "bl": "✦",
            "br": "✦",
            "h": "═",
            "v": "║",
            "ml": "╠",
            "mr": "╣",
            "corner": "✦",
        }
    if rank == 6:
        return {
            "tl": "✧",
            "tr": "✧",
            "bl": "✧",
            "br": "✧",
            "h": "═",
            "v": "║",
            "ml": "╠",
            "mr": "╣",
            "corner": "✧",
        }
    if rank == 7:
        return {
            "tl": "✪",
            "tr": "✪",
            "bl": "✪",
            "br": "✪",
            "h": "═",
            "v": "║",
            "ml": "╠",
            "mr": "╣",
            "corner": "✪",
        }
    return {
        "tl": "◈",
        "tr": "◈",
        "bl": "◈",
        "br": "◈",
        "h": "═",
        "v": "║",
        "ml": "╠",
        "mr": "╣",
        "corner": "◈",
    }


def _wrap_frame(inner_lines: Sequence[str], style: Mapping[str, str], width: int) -> List[str]:
    h = style["h"]
    v = style["v"]
    inner_w = width - 2
    top = f"{style['tl']}{h * inner_w}{style['tr']}"
    bot = f"{style['bl']}{h * inner_w}{style['br']}"
    out = [top]
    for line in inner_lines:
        if line == "---":
            out.append(f"{style['ml']}{h * inner_w}{style['mr']}")
            continue
        out.append(f"{v}{pad_to_width(str(line), inner_w)}{v}")
    out.append(bot)
    return out


def _ornament_header(rank: int, title: str, width: int) -> List[str]:
    """Extra banner lines above the main box for high ranks."""
    if rank <= 2:
        return []
    if rank == 3:
        bar = "·" * min(width, 24)
        return [f"  {bar}", f"   ◆ {title} ◆", f"  {bar}"]
    if rank == 4:
        return [
            "  ★ · · · · · · · · · · · ★",
            f"     ★  {title}  ★",
            "  ★ · · · · · · · · · · · ★",
        ]
    if rank == 5:
        return [
            "  ✦════════════════════════✦",
            f"  ║   ⚔  {title}  ⚔   ║",
            "  ✦════════════════════════✦",
        ]
    if rank == 6:
        return [
            "  ✧░▒▓████████████████▓▒░✧",
            f"  ✧    {title}    ✧",
            "  ✧░▒▓████████████████▓▒░✧",
        ]
    if rank == 7:
        return [
            "  ✪◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉✪",
            f"  ✪   《 {title} 》   ✪",
            "  ✪◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉◉✪",
        ]
    return [
        "  ◈════════════════════════════◈",
        "  ║  ░▒▓  ป ฐ ม ก า ล  ▓▒░  ║",
        f"  ║     {title}     ║",
        "  ◈════════════════════════════◈",
    ]


def format_equipment_list_line(
    index: int,
    item_id: str,
    display_name: str,
    rarity_id: str,
    reg: Optional[DataRegistry],
    *,
    hint: str = "",
) -> str:
    """
    One equipment row for bag category list.
    Shows: index · short code (sw001) · name · [tag] ชื่อระดับ · optional hint.
    """
    from game.domain.item_codes import item_code, rarity_observe_tag

    meta = _tier_meta(reg, rarity_id)
    rank = meta["rank"]
    code = item_code(item_id, reg)
    obs = rarity_observe_tag(reg, rarity_id)
    # strip duplicate rarity from display_name if present — keep base name soft
    base = display_name
    hint_s = f"  {hint}" if hint else ""
    return f"  {index}. {code}  {base}  {obs}  (Lv.{rank}){hint_s}"


def format_gear_showcase(
    item_id: str,
    reg: DataRegistry,
    *,
    rarity: Optional[str] = None,
    width: int = UI_WIDTH,
) -> List[str]:
    """
    Full premium text card for one gear piece.
    Used when player opens bag → equipment → picks id/number.
    """
    from game.domain.equipment import item_by_id
    from game.domain.rarity import (
        display_item_name,
        format_rarity_tag,
        item_default_rarity,
        rarity_stat_mult,
        scaled_item_stats,
    )

    it = item_by_id(reg, item_id) or reg.items.get(item_id) or {}
    if not it and item_id not in (reg.cards or {}):
        return [f"ไม่รู้จักไอเทม ({item_id})"]

    if not it:
        it = reg.cards.get(item_id) or {}

    name = str(it.get("name") or item_id)
    rid = str(rarity or item_default_rarity(it, reg) or "common")
    meta = _tier_meta(reg, rid)
    rank = meta["rank"]
    shown = display_item_name(name, rid, reg)
    style = _frame_style(rank)
    epithet = _EPITHETS.get(meta["id"], _EPITHETS["common"])
    grade_soft = _GRADE_LABEL.get(meta["id"], "เกรดพิเศษ")
    slot = str(it.get("slot") or "")
    glyph = _slot_glyph(slot)

    w = max(40, min(width, 64))
    lines_out: List[str] = []

    # Banner for higher tiers
    title_short = name if display_width(name) <= 18 else name[:12] + "…"
    for bl in _ornament_header(rank, title_short, w):
        lines_out.append(bl)

    # Inner card content
    inner: List[str] = []
    if rank >= 5:
        inner.append(f" {glyph}  {shown}")
        inner.append(f"    « {grade_soft} »")
    elif rank >= 3:
        inner.append(f" {glyph} {shown}")
    else:
        inner.append(f" {shown}")

    from game.domain.item_codes import item_code, rarity_observe_tag

    code = item_code(item_id, reg)
    inner.append("---")
    inner.append(f" ไอดี: {code}   (ระบบ: {item_id})")
    inner.append(f" ระดับอาวุธ: Lv.{rank}  {rarity_observe_tag(reg, rid)}")
    inner.append(f" เกรด: {grade_soft}")
    # soft teach: symbol alone is easy to miss
    inner.append(f"  อ่านระดับ: สัญลักษณ์{meta['tag']} = {meta['name']} (อย่ามองข้ามชื่อไทย)")

    if it.get("desc"):
        inner.append("---")
        inner.append(f" {it.get('desc')}")

    # Stats (scaled) — armor: DEF/MDEF shown; latent HP% never listed
    if any(it.get(k) for k in ("atk", "max_hp", "max_mana", "def", "defense", "mdef")):
        st = scaled_item_stats(it, rid, reg, upgrade_level=0, slot=slot or "weapon")
        bits = []
        if st.get("atk"):
            bits.append(f"โจมตี +{st['atk']}")
        if st.get("def"):
            bits.append(f"กันกาย +{st['def']}")
        if st.get("mdef"):
            bits.append(f"กันเวท +{st['mdef']}")
        # explicit max_hp only (not latent)
        if st.get("max_hp") and int(it.get("max_hp") or 0) > 0 and not it.get("latent_hp_pct"):
            bits.append(f"HP +{st['max_hp']}")
        if st.get("max_mana"):
            bits.append(f"MP +{st['max_mana']}")
        mult = rarity_stat_mult(reg, rid)
        if bits:
            inner.append("---")
            if rank >= 4:
                inner.append(" คุณสมบัติ ✦ " + " · ".join(bits))
            else:
                inner.append(" คุณสมบัติ: " + " · ".join(bits))
            # soft power feel only — mult as flavor band
            if rank <= 1:
                inner.append(" พลัง: มาตรฐาน")
            elif rank <= 3:
                inner.append(f" พลัง: สูงขึ้น (×{mult:.2f})")
            elif rank <= 5:
                inner.append(f" พลัง: อลังการ (×{mult:.2f})")
            else:
                inner.append(f" พลัง: เหนือชั้น (×{mult:.2f})")
        # latent never listed as numbers — soft observation only
        if st.get("def") or st.get("mdef") or it.get("latent_hp_pct"):
            if it.get("latent_hp_pct") or st.get("latent_tough") or st.get("latent_status_resist"):
                inner.append(" …เกราะอุ้มร่าง/อึดอะไรบางอย่าง (สังเกตเลือด·ทนสถานะเอง)")
        if st.get("atk") and (st.get("latent_atk_pct") or st.get("latent_crit") or not it.get("def")):
            if float(st.get("latent_atk_pct") or 0) > 0 or float(st.get("latent_crit") or 0) > 0:
                inner.append(" …คมแฝงอะไรบางอย่าง (สังเกตแรงโจมตี·คริในไฟต์)")

    if slot:
        from game.domain.equipment import SLOT_LABEL_TH, normalize_slot

        ns = normalize_slot(str(slot))
        slot_th = SLOT_LABEL_TH.get(ns) or SLOT_LABEL_TH.get(str(slot)) or str(slot)
        inner.append(f" ช่องสวม: {slot_th}")
    if it.get("sockets"):
        socks = "○" * int(it["sockets"]) if rank < 4 else "◉" * int(it["sockets"])
        inner.append(f" ช่องการ์ด: {it.get('sockets')}  [{socks}]")
    if it.get("set_id"):
        sdef = (getattr(reg, "gear_sets", None) or {}).get(it["set_id"]) or {}
        inner.append(f" เซ็ต: {sdef.get('name') or it['set_id']}")
    if it.get("tags"):
        inner.append(" แท็ก: " + ", ".join(str(t) for t in it["tags"]))

    # Art + epithet
    is_gear = str(it.get("kind") or "") == "equipment" or slot in (
        "weapon",
        "armor",
        "accessory",
    )
    if is_gear and (slot == "weapon" or not slot):
        inner.append("---")
        for art_line in _sword_art(rank):
            inner.append(f" {art_line}")

    inner.append("---")
    # Epithet with increasing emphasis
    if rank <= 1:
        inner.append(f" {epithet}")
    elif rank <= 3:
        inner.append(f" 「{epithet}」")
    elif rank <= 5:
        inner.append(f" 『{epithet}』")
    else:
        inner.append(f" ❝ {epithet} ❞")
        if rank >= 7:
            inner.append(" ─ ความพิเศษนี้… แม้ตัวอักษรก็สั่นไหว ─")

    # Prestige footer
    if rank >= 5:
        stars = meta["tag"] * min(rank, 8)
        inner.append(f" {stars}")
    elif rank >= 3:
        inner.append(f" {meta['tag']} · หายากในโลกเปิด · {meta['tag']}")

    framed = _wrap_frame(inner, style, w)
    lines_out.extend(framed)

    # Extra outer aura for mythic/archdivine
    if rank >= 7:
        aura = style["corner"] + "·" * (w - 2) + style["corner"]
        lines_out.insert(0, aura)
        lines_out.append(aura)
    elif rank >= 5:
        lines_out.append(f"  {meta['tag']}  ของชิ้นนี้โดดเด่นจากอาวุธธรรมดาชัดเจน  {meta['tag']}")

    return lines_out


def format_examine_with_showcase(
    item_id: str,
    reg: DataRegistry,
    *,
    rarity: Optional[str] = None,
    howto: bool = True,
) -> List[str]:
    """
    Showcase card + short how-to (equipment-focused).
    Non-equipment falls back to plain showcase without sword art still OK.
    """
    lines = format_gear_showcase(item_id, reg, rarity=rarity)
    it = reg.items.get(item_id) or {}
    kind = str(it.get("kind") or "")
    if not howto:
        return lines
    lines = list(lines)
    lines.append("")
    if kind == "equipment" or it.get("slot") in ("weapon", "armor", "accessory"):
        lines.append(" วิธีใช้: 1.สวม  ·  0.กลับ")
        lines.append("  · อัปเกรดได้เมื่อสวมอยู่ (อัตราสำเร็จไม่คงที่)")
    elif kind == "material" or "mat" in item_id:
        lines.append(" วิธีใช้: วัตถุดิบ — ใช้ตอนคราฟ/อัปเกียร์ (ใช้ตรงไม่ได้)")
    else:
        lines.append(" วิธีใช้: ดูรายละเอียด · กลับด้วย 0")
    return lines

"""Standard result panels — victory, soft death, approach outcome (UIUX B)."""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

from game.ui_terminal.layout import render_box


def victory_panel(
    lines: Sequence[str],
    *,
    title: str = "ชนะ",
) -> str:
    body = [f" ✦ {title} ✦", "---", *[f" {x}" if not str(x).startswith(" ") else str(x) for x in lines]]
    return render_box(body, double=False)


def soft_death_panel(summary: str, extra: Optional[Sequence[str]] = None) -> str:
    lines = [
        " ✦ ล้มลง — แต่ยังไม่จบ ✦",
        "---",
        f" {summary}",
    ]
    for e in extra or []:
        lines.append(f" {e}")
    lines.append(" ฟื้นในจุดปลอดภัย — ของบางอย่างอาจสูญเสีย")
    return render_box(lines, double=True)


def approach_outcome_line(kind: str, outcome: str) -> str:
    """One-line soft summary after approach (no % spoiler)."""
    k = str(kind or "")
    o = str(outcome or "")
    table = {
        ("monster", "flee"): "▸ ผล: มันหนี — คุณได้แค่เค้าโครงเลือนๆ",
        ("monster", "rare_talk"): "▸ ผล: สื่อสารแปลกๆ ได้ — ชำนาญพื้นที่งอกเงย",
        ("monster", "ambush"): "▸ ผล: ถูกซุ่ม — เข้าไฟต์เสียเปรียบ",
        ("monster", "fair_combat"): "▸ ผล: ปะทะตรงๆ — เริ่มต่อสู้",
        ("chest", "ambush"): "▸ ผล: หีบปลอม — มอนโผล่!",
        ("chest", "empty_trap"): "▸ ผล: กับดัก — ระวังสถานะผิดปกติ",
        ("chest", "rare_relic"): "▸ ผล: โชคดี — ของ/เงินคุณภาพดี",
        ("chest", "loot_weak"): "▸ ผล: ของเล็กน้อยในหีบ",
        ("chest", "empty"): "▸ ผล: หีบว่างเปล่า",
        ("npc", "friend"): "▸ ผล: มิตรภาพ — ได้แรงหนุนชั่วคราว",
        ("npc", "shop"): "▸ ผล: พบพ่อค้า",
        ("npc", "master"): "▸ ผล: พบอาจารย์",
        ("npc", "hostile"): "▸ ผล: ศัตรูปลอมคน — ไฟต์!",
        ("npc", "trap_disguise"): "▸ ผล: หน้ากากหลุด — ไฟต์!",
        ("npc", "ignore"): "▸ ผล: เขาไม่สนใจคุณ",
    }
    if (k, o) in table:
        return table[(k, o)]
    # soft defaults
    if k == "monster":
        return "▸ ผล: การเผชิญหน้าจบลงอย่างหนึ่ง"
    if k == "chest":
        return "▸ ผล: เปิดหีบแล้ว — ผลไม่เหมือนทุกครั้ง"
    if k == "npc":
        return "▸ ผล: การสนทนาจบลง"
    return "▸ ผล: สถานการณ์ผ่านไป"


def soft_enemy_vitality(mon: Mapping[str, Any], *, known: bool = False) -> str:
    """Soft band without spoiling exact HP when unknown."""
    hp = int(mon.get("hp") or 0)
    mx = max(1, int(mon.get("max_hp") or 1))
    r = hp / mx
    if known or mon.get("boss"):
        if r <= 0:
            return "ศัตรู: ล้มแล้ว"
        if r <= 0.2:
            return "ศัตรู: ใกล้พัง"
        if r <= 0.45:
            return "ศัตรู: สะท้านชัด"
        if r <= 0.75:
            return "ศัตรู: ยังไหว"
        return "ศัตรู: ยังแข็ง"
    # unknown — softer words, no numbers
    if r <= 0.2:
        return "เงาตรงข้าม: เหมือนจะพังทลาย"
    if r <= 0.45:
        return "เงาตรงข้าม: ท่าทางสะท้าน"
    if r <= 0.75:
        return "เงาตรงข้าม: ยังทรงตัว"
    return "เงาตรงข้าม: ยังแน่นิ่งอ่านยาก"

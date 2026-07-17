"""
Combat skill picker + combo result layout (readable, proportional boxes).

Soft feel: short columns, wrap chain, group result lines — no % spoilers.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence, Tuple

from game.config import UI_WIDTH
from game.ui_terminal.layout import display_width, pad_to_width, render_box


def _trunc(text: str, width: int) -> str:
    text = str(text or "")
    if display_width(text) <= width:
        return text
    out: List[str] = []
    w = 0
    for ch in text:
        cw = display_width(ch)
        if w + cw > max(1, width - 1):
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


def _wrap_arrow_chain(names: Sequence[str], *, inner: int = 54) -> List[str]:
    """Wrap 'A → B → C' across lines without mid-name breaks."""
    if not names:
        return ["  (ว่าง)"]
    lines: List[str] = []
    cur = "  " + str(names[0])
    for nm in names[1:]:
        piece = f" → {nm}"
        if display_width(cur) + display_width(piece) <= inner:
            cur += piece
        else:
            lines.append(cur)
            cur = "  → " + str(nm)
    lines.append(cur)
    return lines


def format_skill_menu_lines(
    opts: Sequence[Tuple[str, Mapping[str, Any]]],
    player: Mapping[str, Any],
    reg: Any,
    *,
    max_combo: int = 3,
    format_charge_hint=None,
) -> List[str]:
    """
    Lines for render_box — skill list + how to type combo.
    """
    mp_now = int(player.get("mana") or 0)
    mp_max = max(0, int(player.get("max_mana") or 0))
    lines: List[str] = [
        " สกิล / คอมโบ",
        "---",
        f" มานาตอนนี้  {mp_now}/{mp_max}      โซ่สูงสุด  {max_combo} ขั้น",
        "---",
    ]

    # columns: # | name | MP | note  (inner width ~58)
    num_w, mp_w, note_w = 3, 5, 12
    name_w = max(14, 54 - num_w - mp_w - note_w - 4)

    lines.append(
        " "
        + pad_to_width("#", num_w)
        + " "
        + pad_to_width("ท่า", name_w)
        + " "
        + pad_to_width("MP", mp_w)
        + " "
        + pad_to_width("หมายเหตุ", note_w)
    )

    for i, (sid, sk) in enumerate(opts, 1):
        cost = int(sk.get("cost_mana", 0) or 0)
        name = str(sk.get("name") or sid)
        chg = ""
        if callable(format_charge_hint):
            try:
                chg = str(format_charge_hint(player, sid, reg) or "")
            except Exception:
                chg = ""
        if chg:
            name = f"{name}{chg}"

        tags: List[str] = []
        if not sk.get("combo_ok", True):
            tags.append("นอกโซ่")
        if sk.get("aoe"):
            tags.append("AoE")
        slot = str(sk.get("slot") or "combat")
        slot_map = {"buff": "บัฟ", "debuff": "ดีบัฟ", "support": "ซัพ"}
        if slot in slot_map:
            tags.append(slot_map[slot])
        rank_lab = str(sk.get("_rank_label") or "")
        if rank_lab and rank_lab not in ("", "ธรรมดา"):
            tags.append(rank_lab)

        mp_s = str(cost)
        if cost > mp_now:
            mp_s = f"{cost}!"

        tag_s = "·".join(tags) if tags else "—"
        lines.append(
            " "
            + pad_to_width(str(i), num_w)
            + " "
            + pad_to_width(_trunc(name, name_w), name_w)
            + " "
            + pad_to_width(mp_s, mp_w)
            + " "
            + pad_to_width(_trunc(tag_s, note_w), note_w)
        )

    lines.append("---")
    lines.append(f" พิมพ์เลขคั่นช่องว่าง · สูงสุด {max_combo} ขั้น")
    lines.append("  ตัวอย่าง  3          ท่าเดียว")
    if max_combo >= 3:
        lines.append("            3 5 6      โซ่ 3 ขั้น")
    lines.append("  0 / ว่าง = ยกเลิก")
    return lines


def format_combo_open_lines(
    *,
    length: int,
    chain_names: Sequence[str],
    flavor: str = "",
    mind_notes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Header block before damage numbers."""
    if length >= 2:
        title = f" คอมโบ  {length} ขั้น"
    else:
        nm = chain_names[0] if chain_names else "สกิล"
        title = f" ลงมือ  ·  {nm}"

    lines: List[str] = [title, "---"]
    if length >= 2:
        lines.append(" โซ่")
        lines.extend(_wrap_arrow_chain(chain_names))
        lines.append("---")
    if flavor:
        fl = str(flavor).strip()
        if fl:
            lines.append(" หลอม / จังหวะ")
            # wrap flavor soft
            inner = 54
            if display_width(fl) <= inner:
                lines.append(f"  {fl}")
            else:
                # soft wrap by spaces
                words = fl.split()
                cur = "  "
                for w in words:
                    trial = (cur + " " + w).strip() if cur.strip() else "  " + w
                    trial = "  " + trial.strip()
                    if display_width(trial) <= inner:
                        cur = trial
                    else:
                        if cur.strip():
                            lines.append(cur)
                        cur = "  " + w
                if cur.strip():
                    lines.append(cur)
            lines.append("---")
    for n in mind_notes or []:
        s = str(n).strip()
        if s:
            if not s.startswith("…") and not s.startswith("."):
                s = "…" + s
            lines.append(f" {s}")
    return lines


def format_combo_result_lines(
    *,
    damage: int = 0,
    heal: int = 0,
    mana_cost: int = 0,
    length: int = 1,
    flavor_tag: str = "",
    enemy_soft: str = "",
    status_line: str = "",
    resist_line: str = "",
    fight_log_line: str = "",
    extra: Optional[Sequence[str]] = None,
) -> List[str]:
    """Numbers / outcome block after narrative hit."""
    lines: List[str] = [" ผล", "---"]
    if heal > 0:
        lines.append(f"  ฟื้นฟู   +{heal} HP")
        lines.append(f"  มานา    −{mana_cost}")
    elif damage > 0:
        tag = str(flavor_tag or "").strip()
        dmg_line = f"  ดาเมจ   {damage}"
        if tag:
            dmg_line += f"  {tag}"
        lines.append(dmg_line)
        lines.append(f"  มานา    −{mana_cost}    ·    {length} ขั้น")
    else:
        lines.append(f"  ใช้ท่า   (ไม่มีดาเมจตรง)")
        lines.append(f"  มานา    −{mana_cost}")

    if fight_log_line:
        fl = str(fight_log_line).strip()
        if fl:
            lines.append("---")
            lines.append(f"  {fl}")

    if enemy_soft:
        es = str(enemy_soft).strip()
        if es:
            # soft_enemy_vitality already prefixes ศัตรู:/เงา…
            lines.append(f"  {es}")

    if status_line:
        lines.append(f"  สถานะ   {status_line}")
    if resist_line:
        lines.append(f"  ศัตรู    {resist_line}")

    for x in extra or []:
        s = str(x).strip()
        if s:
            lines.append(f"  {s}" if not s.startswith(" ") else s)
    return lines


def format_party_assist_header() -> str:
    return " ซุ่มช่วย · ตามสัมพันธ์สหาย"


# ── Combat bag / consumable picker (เมนู 3) ─────────────────────────────


def consumable_effect_hint(it: Mapping[str, Any], *, item_id: str = "") -> str:
    """Short soft effect for list column — no %."""
    it = it or {}
    iid = str(item_id or it.get("id") or "")
    # Recovery multi-turn
    rk = str(it.get("recovery_kind") or "").lower()
    rr = str(it.get("recovery_rank") or "").upper()
    if rk and rr:
        kind = {"hp": "HP", "mp": "MP", "py": "ล้า"}.get(rk, rk.upper())
        dur = 3 if rr == "S" else 5
        if rr == "S":
            return f"ฟื้น{kind}เต็ม/{dur}เทิร์น"
        return f"ฟื้น{kind} ·{rr} ·{dur}เทิร์น"
    bits: List[str] = []
    if it.get("heal_hp"):
        bits.append(f"HP+{int(it['heal_hp'])}")
    if it.get("heal_mana"):
        bits.append(f"MP+{int(it['heal_mana'])}")
    if it.get("clear_all_debuffs") or str(it.get("clear_status") or "").lower() in (
        "all",
        "*",
        "debuff",
    ):
        bits.append("ล้างสถานะ")
    elif it.get("clear_status"):
        bits.append(f"ล้าง{it.get('clear_status')}")
    st = it.get("apply_status") or it.get("food_buff")
    if st:
        sid = st.get("id") if isinstance(st, dict) else st
        bits.append(f"บัฟ {sid}")
    if it.get("food_tier") or it.get("hunger_relief") or (
        isinstance(it.get("tags"), (list, tuple)) and "food" in (it.get("tags") or [])
    ):
        if not any("HP" in b or "MP" in b for b in bits):
            bits.append("อาหาร")
        else:
            bits.append("กิน")
    if it.get("restore_intel") or it.get("fill_intel") or it.get("boost_intel_max"):
        bits.append("จิต")
    if not bits:
        # name heuristics
        nm = str(it.get("name") or iid)
        if "มานา" in nm or "Mana" in nm:
            bits.append("MP")
        elif "HP" in nm or "เลือด" in nm:
            bits.append("HP")
        elif "พิษ" in nm or "แก้" in nm:
            bits.append("ล้าง")
        else:
            bits.append("ใช้ได้")
    return " · ".join(bits[:3])


def consumable_kind_tag(it: Mapping[str, Any]) -> str:
    it = it or {}
    if it.get("recovery_kind"):
        return "ฟื้น"
    if it.get("food_tier") or it.get("hunger_relief"):
        return "อาหาร"
    if it.get("clear_all_debuffs") or (
        it.get("clear_status") and not it.get("heal_hp") and not it.get("heal_mana")
    ):
        return "ล้าง"
    if it.get("apply_status") and not it.get("heal_hp") and not it.get("heal_mana"):
        return "บัฟ"
    if it.get("restore_intel") or it.get("fill_intel") or it.get("boost_intel_max"):
        return "จิต"
    if it.get("heal_mana") and not it.get("heal_hp"):
        return "ยาMP"
    if it.get("heal_hp"):
        return "ยาHP"
    return "ของใช้"


def format_consumable_menu_lines(
    entries: Sequence[Mapping[str, Any]],
    player: Mapping[str, Any],
    *,
    free_action: bool = True,
) -> List[str]:
    """
    entries: [{index_label, name, effect, kind}]  index_label is 1-based display.
    """
    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    mp = int(player.get("mana") or 0)
    mmp = max(0, int(player.get("max_mana") or 0))
    fat = "—"
    try:
        from game.domain.needs import get_needs, soft_label

        n = get_needs(player)
        fat = soft_label("fatigue", int(n.get("fatigue") or 0))
    except Exception:
        pass

    lines: List[str] = [
        " ของใช้ในไฟต์",
        "---",
        f" HP  {hp}/{mhp}    MP  {mp}/{mmp}    ล้า  {fat}",
    ]
    if free_action:
        lines.append(" ใช้แล้วไม่เสียเทิร์น · เลือกคำสั่งต่อได้")
    lines.append("---")

    num_w, kind_w, name_w = 3, 6, 22
    eff_w = 20
    lines.append(
        " "
        + pad_to_width("#", num_w)
        + " "
        + pad_to_width("ชนิด", kind_w)
        + " "
        + pad_to_width("ชื่อ", name_w)
        + " "
        + "ผล"
    )
    lines.append("---")

    if not entries:
        lines.append(" (ว่าง — ไม่มีของใช้ได้)")
        lines.append("---")
        lines.append(" 0  กลับ")
        return lines

    for e in entries:
        n = str(e.get("n") or "")
        kind = str(e.get("kind") or "")
        name = _trunc(str(e.get("name") or "?"), name_w)
        eff = _trunc(str(e.get("effect") or ""), eff_w)
        lines.append(
            " "
            + pad_to_width(n, num_w)
            + " "
            + pad_to_width(kind, kind_w)
            + " "
            + pad_to_width(name, name_w)
            + " "
            + eff
        )

    lines.append("---")
    lines.append(" พิมพ์เลขเพื่อใช้  ·  0 กลับ")
    return lines


def render_consumable_menu_box(
    entries: Sequence[Mapping[str, Any]],
    player: Mapping[str, Any],
    *,
    free_action: bool = True,
    width: int = UI_WIDTH,
) -> str:
    return render_box(
        format_consumable_menu_lines(entries, player, free_action=free_action),
        width=width,
        double=False,
    )


def format_item_care_hub_lines(player: Mapping[str, Any]) -> List[str]:
    """Submenu 3 hub — proportional care panel."""
    hp = int(player.get("hp") or 0)
    mhp = max(1, int(player.get("max_hp") or 1))
    mp = int(player.get("mana") or 0)
    mmp = max(0, int(player.get("max_mana") or 0))
    return [
        " ยา / ล้าง / บัฟ",
        "---",
        f" HP  {hp}/{mhp}    ·    MP  {mp}/{mmp}",
        "---",
        "  1  ใช้ของจากคลัง",
        "  2  ล้างเร็ว          (ยาแก้พิษ / ถอนสถานะ)",
        "  0  กลับไฟต์",
        "---",
        " ไม่เสียเทิร์น  ·  เหมือนประเมิน I",
    ]


def render_item_care_hub_box(player: Mapping[str, Any], *, width: int = UI_WIDTH) -> str:
    return render_box(format_item_care_hub_lines(player), width=width, double=False)


def format_item_use_result_lines(
    *,
    name: str,
    effect_lines: Sequence[str],
    free_action: bool = True,
) -> List[str]:
    lines: List[str] = [
        " ใช้ของแล้ว",
        "---",
        f" 「{_trunc(name, 48)}」",
        "---",
    ]
    for e in effect_lines:
        s = str(e).strip()
        if s:
            lines.append(f"  {s}")
    if free_action:
        lines.append("---")
        lines.append(" ไม่เสียเทิร์น — เลือกคำสั่งต่อได้")
    return lines


def render_item_use_result_box(
    *,
    name: str,
    effect_lines: Sequence[str],
    free_action: bool = True,
    width: int = UI_WIDTH,
) -> str:
    return render_box(
        format_item_use_result_lines(
            name=name, effect_lines=effect_lines, free_action=free_action
        ),
        width=width,
        double=False,
    )


def render_skill_menu_box(
    opts: Sequence[Tuple[str, Mapping[str, Any]]],
    player: Mapping[str, Any],
    reg: Any,
    *,
    max_combo: int = 3,
    format_charge_hint=None,
    width: int = UI_WIDTH,
) -> str:
    return render_box(
        format_skill_menu_lines(
            opts,
            player,
            reg,
            max_combo=max_combo,
            format_charge_hint=format_charge_hint,
        ),
        width=width,
        double=False,
    )


def render_combo_open_box(
    *,
    length: int,
    chain_names: Sequence[str],
    flavor: str = "",
    mind_notes: Optional[Sequence[str]] = None,
    width: int = UI_WIDTH,
) -> str:
    return render_box(
        format_combo_open_lines(
            length=length,
            chain_names=chain_names,
            flavor=flavor,
            mind_notes=mind_notes,
        ),
        width=width,
        double=False,
    )


def render_combo_result_box(
    *,
    damage: int = 0,
    heal: int = 0,
    mana_cost: int = 0,
    length: int = 1,
    flavor_tag: str = "",
    enemy_soft: str = "",
    status_line: str = "",
    resist_line: str = "",
    fight_log_line: str = "",
    extra: Optional[Sequence[str]] = None,
    width: int = UI_WIDTH,
) -> str:
    return render_box(
        format_combo_result_lines(
            damage=damage,
            heal=heal,
            mana_cost=mana_cost,
            length=length,
            flavor_tag=flavor_tag,
            enemy_soft=enemy_soft,
            status_line=status_line,
            resist_line=resist_line,
            fight_log_line=fight_log_line,
            extra=extra,
        ),
        width=width,
        double=False,
    )

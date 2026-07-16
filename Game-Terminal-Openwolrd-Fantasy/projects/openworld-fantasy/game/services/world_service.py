"""World entry: independent worlds, latest save, rankings, custom world create (WO-002)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from game.data_load.registry import DataRegistry
from game.domain.world_creation import (
    allocate_custom_world_id,
    apply_world_theme_to_player,
    area_display_name,
    build_custom_profile,
    ensure_catalog_profile,
    list_custom_world_ids,
    list_themes,
    load_world_profile,
    resolve_world_def,
    save_world_profile,
    soft_flavor_lines,
    theme_by_id,
    theme_for_catalog_world,
    world_theme_ux_enabled,
)
from game.ports.io import IO
from game.services.save_service import list_saves, load_player
from game.ui_terminal.layout import render_box


def world_summary_lines(reg: DataRegistry, world_id: str) -> List[str]:
    """Simple summary by default; theme/flavor only if WO-002 UX re-enabled."""
    if not world_theme_ux_enabled():
        w = reg.worlds.get(world_id) or {}
        saves = list_saves(world_id)
        latest = latest_save_meta(world_id)
        lines = [
            f"โลก: {w.get('name', world_id)}",
            f"ความยาก: {w.get('difficulty_label', w.get('difficulty', '?'))}",
            f"จุดเริ่ม: {w.get('starting_area', '?')}",
            f"อิสระ: {'ใช่' if w.get('independent', True) else 'ไม่'}",
            f"ตัวละครในโลก: {len(saves)}",
        ]
        if latest:
            lines.append(
                f"เซฟล่าสุด: {latest.get('name')} @ {latest.get('location')} "
                f"({latest.get('updated_at') or '—'})"
            )
        else:
            lines.append("เซฟล่าสุด: (ยังไม่มี — ต้องสร้างตัวใหม่)")
        return lines

    wdef = resolve_world_def(reg, world_id)
    theme = theme_by_id(str(wdef.get("theme_id") or "")) or theme_for_catalog_world(
        world_id, reg
    )
    saves = list_saves(world_id)
    latest = latest_save_meta(world_id)
    start = str(wdef.get("starting_area") or "?")
    start_name = area_display_name(reg, start) if start != "?" else "?"
    lines = [
        f"โลก: {wdef.get('name', world_id)}",
        f"ความยาก: {wdef.get('difficulty_label', wdef.get('difficulty', '?'))}",
        f"จุดเริ่ม: {start_name}",
    ]
    if theme:
        lines.append(f"ธีม: {theme.get('name') or theme.get('id')}")
    src = str(wdef.get("source") or "catalog")
    if src == "custom":
        lines.append("กำเนิด: สร้างโดยคุณ")
    else:
        lines.append(f"อิสระ: {'ใช่' if wdef.get('independent', True) else 'ไม่'}")
    lines.append(f"ตัวละครในโลก: {len(saves)}")
    if latest:
        lines.append(
            f"เซฟล่าสุด: {latest.get('name')} @ {latest.get('location')} "
            f"({latest.get('updated_at') or '—'})"
        )
    else:
        lines.append("เซฟล่าสุด: (ยังไม่มี — ต้องสร้างตัวใหม่)")
    for fl in soft_flavor_lines(theme, max_lines=2):
        lines.append(f"…{fl}")
    if theme and theme.get("soft_skill_hint"):
        lines.append(f"open skill: {theme.get('soft_skill_hint')}")
    return lines


def latest_save_meta(world_id: str) -> Optional[Dict[str, Any]]:
    saves = list_saves(world_id)
    if not saves:
        return None

    def key(s: Dict[str, Any]) -> str:
        return str(s.get("updated_at") or "")

    return max(saves, key=key)


def enter_world_latest(world_id: str) -> Optional[Dict[str, Any]]:
    meta = latest_save_meta(world_id)
    if not meta:
        return None
    return load_player(meta["path"])


def list_world_menu_rows(reg: DataRegistry) -> List[Dict[str, Any]]:
    """Catalog worlds; custom worlds only when WO-002 UX is enabled."""
    rows: List[Dict[str, Any]] = []
    seen = set()

    for wid, w in (reg.worlds or {}).items():
        latest = latest_save_meta(wid)
        theme = theme_for_catalog_world(wid, reg) if world_theme_ux_enabled() else None
        rows.append(
            {
                "id": wid,
                "name": w.get("name", wid),
                "difficulty_label": w.get("difficulty_label", "?"),
                "difficulty": int(w.get("difficulty", 1)),
                "description": w.get("description", ""),
                "has_save": latest is not None,
                "latest_name": (latest or {}).get("name"),
                "latest_location": (latest or {}).get("location"),
                "char_count": len(list_saves(wid)),
                "source": "catalog",
                "theme_id": (theme or {}).get("id") if theme else None,
                "theme_name": (theme or {}).get("name") if theme else None,
                "starting_area": w.get("starting_area"),
                "soft_flavor": soft_flavor_lines(theme, max_lines=1) if theme else [],
            }
        )
        seen.add(str(wid))

    if world_theme_ux_enabled():
        for wid in list_custom_world_ids():
            if wid in seen or wid in (reg.worlds or {}):
                continue
            wdef = resolve_world_def(reg, wid)
            latest = latest_save_meta(wid)
            theme = theme_by_id(str(wdef.get("theme_id") or ""))
            rows.append(
                {
                    "id": wid,
                    "name": wdef.get("name", wid),
                    "difficulty_label": wdef.get("difficulty_label", "?"),
                    "difficulty": int(wdef.get("difficulty") or 1),
                    "description": wdef.get("description", ""),
                    "has_save": latest is not None,
                    "latest_name": (latest or {}).get("name"),
                    "latest_location": (latest or {}).get("location"),
                    "char_count": len(list_saves(wid)),
                    "source": "custom",
                    "theme_id": (theme or {}).get("id") or wdef.get("theme_id"),
                    "theme_name": (theme or {}).get("name") or wdef.get("theme_name"),
                    "starting_area": wdef.get("starting_area"),
                    "soft_flavor": soft_flavor_lines(theme, max_lines=1),
                }
            )
            seen.add(str(wid))

    rows.sort(
        key=lambda r: (0 if r.get("source") == "catalog" else 1, int(r.get("difficulty") or 1))
    )
    return rows


def _difficulty_mark(label: str, difficulty: int) -> str:
    lab = str(label or "")
    d = int(difficulty or 1)
    if d <= 1 or "ปกติ" in lab:
        return "○ ปกติ"
    if d == 2 or "ท้าทาย" in lab:
        return "◇ ท้าทาย"
    if d >= 3 or "ฝันร้าย" in lab or "นรก" in lab:
        return "◆ ฝันร้าย"
    return f"· {lab}"


def format_world_picker_lines(reg: DataRegistry) -> List[str]:
    """
    World picker UI.
    Default (simple): list catalog worlds + difficulty + save status.
    WO-002 full UX only when WORLD_THEME_UX_ENABLED.
    """
    rows = list_world_menu_rows(reg)
    if not world_theme_ux_enabled():
        lines: List[str] = [
            " เลือกโลก",
            "---",
            " เซฟ · อันดับ · ประวัติ แยกกันแต่ละโลก (ไม่ปนกัน)",
            "---",
        ]
        if not rows:
            lines.append(" (ยังไม่มีโลกใน data)")
            return lines
        for i, r in enumerate(rows, 1):
            mark = _difficulty_mark(
                str(r.get("difficulty_label")), int(r.get("difficulty") or 1)
            )
            name = str(r.get("name") or r.get("id") or "?")
            nchar = int(r.get("char_count") or 0)
            if r.get("has_save") and r.get("latest_name"):
                loc = r.get("latest_location") or "?"
                save_line = f" เซฟล่าสุด  {r['latest_name']} @ {loc}"
                if nchar > 1:
                    save_line += f"  (+{nchar - 1} ตัวอื่น)"
            else:
                save_line = " เซฟ       ยังไม่มี — สร้างตัวใหม่ได้"
            lines.append(f" {i}. {name}")
            lines.append(f"    ความยาก  {mark}")
            lines.append(f"   {save_line}")
            desc = str(r.get("description") or "").strip()
            if desc:
                lines.append(f"    หมายเหตุ  {desc}")
            if i < len(rows):
                lines.append("")
        lines.append("---")
        lines.append(f" พิมพ์ 1–{len(rows)} แล้ว Enter")
        lines.append(" 0  ย้อนกลับเมนูหลัก")
        return lines

    # ── WO-002 full picker (disabled by default) ──
    lines = [
        " เลือกโลก",
        "---",
        " เซฟ · อันดับ · ประวัติ แยกกันแต่ละโลก (ไม่ปนกัน)",
        " แต่ละโลกมีธีมพื้นที่ — กระทบชำนาญ / open skill เบาๆ",
        "---",
    ]
    if not rows:
        lines.append(" (ยังไม่มีโลกใน data)")
    for i, r in enumerate(rows, 1):
        mark = _difficulty_mark(str(r.get("difficulty_label")), int(r.get("difficulty") or 1))
        name = str(r.get("name") or r.get("id") or "?")
        nchar = int(r.get("char_count") or 0)
        src = str(r.get("source") or "catalog")
        badge = " · ของคุณ" if src == "custom" else ""
        if r.get("has_save") and r.get("latest_name"):
            loc = r.get("latest_location") or "?"
            save_line = f" เซฟล่าสุด  {r['latest_name']} @ {loc}"
            if nchar > 1:
                save_line += f"  (+{nchar - 1} ตัวอื่น)"
        else:
            save_line = " เซฟ       ยังไม่มี — สร้างตัวใหม่ได้"

        lines.append(f" {i}. {name}{badge}")
        lines.append(f"    ความยาก  {mark}")
        theme_n = r.get("theme_name")
        start = r.get("starting_area")
        if theme_n or start:
            an = area_display_name(reg, str(start)) if start else "?"
            tbit = f"ธีม {theme_n}" if theme_n else "ธีม —"
            lines.append(f"    {tbit}  ·  พื้นที่ {an}")
        lines.append(f"   {save_line}")
        flavors = r.get("soft_flavor") or []
        if flavors:
            lines.append(f"    …{flavors[0]}")
        desc = str(r.get("description") or "").strip()
        if desc and not flavors:
            lines.append(f"    หมายเหตุ  {desc}")
        if i < len(rows):
            lines.append("")

    create_idx = len(rows) + 1
    lines.append("")
    lines.append(f" {create_idx}. ✦ สร้างโลกของฉัน")
    lines.append("    ตั้งชื่อ · เลือกธีมเริ่มต้น · รู้สึกเป็นโลกคุณ")
    lines.append("---")
    lines.append(f" พิมพ์ 1–{create_idx} แล้ว Enter")
    lines.append(" 0  ย้อนกลับเมนูหลัก")
    return lines


def format_save_picker_lines(
    world_id: str,
    world_name: str = "",
) -> List[str]:
    saves = list_saves(world_id)
    title = world_name or world_id
    lines: List[str] = [
        " ตัวละครในโลก",
        "---",
        f" {title}",
        "---",
    ]
    if not saves:
        lines.append(" (ยังไม่มีเซฟในโลกนี้)")
        lines.append("---")
        lines.append(" 0  ย้อนกลับเมนูหลัก")
        return lines
    for i, s in enumerate(saves, 1):
        occ = s.get("occupation") or "?"
        loc = s.get("location") or "?"
        when = s.get("updated_at") or ""
        when_bit = f" · {when}" if when else ""
        lines.append(f" {i}. {s.get('name') or '?'}")
        lines.append(f"    {occ}  @ {loc}{when_bit}")
        if i < len(saves):
            lines.append("")
    lines.append("---")
    lines.append(f" พิมพ์ 1–{len(saves)} แล้ว Enter")
    lines.append(" 0  ย้อนกลับเมนูหลัก")
    return lines


def format_theme_picker_lines(reg: DataRegistry) -> List[str]:
    themes = list_themes()
    lines: List[str] = [
        " เลือกธีมเริ่มต้นของโลก",
        "---",
        " ธีมกำหนดพื้นที่เริ่ม · ชำนาญอุ่น · open skill soft",
        "---",
    ]
    for i, t in enumerate(themes, 1):
        an = area_display_name(reg, str(t.get("starting_area") or ""))
        lines.append(f" {i}. {t.get('name') or t.get('id')}")
        lines.append(f"    พื้นที่เริ่ม  {an}")
        for fl in soft_flavor_lines(t, max_lines=1):
            lines.append(f"    …{fl}")
        hint = str(t.get("soft_skill_hint") or "").strip()
        if hint:
            lines.append(f"    open skill  {hint}")
        if i < len(themes):
            lines.append("")
    lines.append("---")
    lines.append(f" พิมพ์ 1–{len(themes)} แล้ว Enter")
    return lines


def run_create_world_flow(reg: DataRegistry, io: IO) -> Optional[str]:
    """
    Interactive: name world + pick theme → write world_profile.json → return world_id.
    Does not create a character (caller does interactive_create).
    """
    themes = list_themes()
    if not themes:
        io.write_line(" ยังไม่มีธีมโลกใน data — ใช้โลกในรายการแทน")
        return None

    io.write_line()
    io.write_line(
        render_box(
            [
                " สร้างโลกของฉัน  (1/2) ชื่อโลก",
                "---",
                " ชื่อนี้เป็นโลกคุณ — เซฟแยกโฟลเดอร์",
                " (world_id ภายในระบบยังเป็นรหัสโฟลเดอร์)",
            ],
            double=False,
        )
    )
    raw_name = io.read_line("\n  ชื่อโลก: ").strip()
    if not raw_name or raw_name in ("0", "q", "Q"):
        io.write_line("  ยกเลิกสร้างโลก")
        return None
    display_name = raw_name[:48]

    io.write_line()
    io.write_line(render_box(format_theme_picker_lines(reg), double=False))
    theme = themes[0]
    for _ in range(6):
        ch = io.read_line(f"\n  เลือกธีม (1–{len(themes)}): ").strip()
        if ch in ("0", "q", "Q"):
            io.write_line("  ยกเลิกสร้างโลก")
            return None
        try:
            idx = int(ch) - 1
            if 0 <= idx < len(themes):
                theme = themes[idx]
                break
        except Exception:
            pass
        io.write_line("  เลือกหมายเลขธีมให้ถูกต้อง")

    world_id = allocate_custom_world_id(display_name)
    # avoid overwriting catalog ids
    if world_id in (reg.worlds or {}):
        world_id = allocate_custom_world_id(display_name + "_x")

    profile = build_custom_profile(
        display_name=display_name,
        theme=theme,
        world_id=world_id,
    )
    save_world_profile(profile)

    an = area_display_name(reg, str(profile.get("starting_area")))
    io.write_line()
    io.write_line(
        render_box(
            [
                " โลกถูกสร้างแล้ว",
                "---",
                f" ชื่อ  {profile.get('name')}",
                f" ธีม  {theme.get('name')}",
                f" จุดเริ่ม  {an}",
                f" รหัสโฟลเดอร์  {world_id}",
                "---",
                " ต่อไป: สร้างตัวละครในโลกนี้",
                " …คุณกำลังเปิดเส้นทาง open skill ของโลกตัวเอง",
            ],
            double=False,
        )
    )
    for fl in soft_flavor_lines(theme, max_lines=2):
        io.write_line(f"  …{fl}")
    io.read_line("\n  Enter เพื่อสร้างตัวละคร...")
    return world_id


def pick_world_interactive(reg: DataRegistry, io: IO) -> Optional[str]:
    """
    World picker. Simple catalog list by default.
    Create-my-world only when WORLD_THEME_UX_ENABLED.
    """
    rows = list_world_menu_rows(reg)
    io.write_line()
    io.write_line(render_box(format_world_picker_lines(reg), double=False))
    n = len(rows)
    if not n:
        return None
    use_create = world_theme_ux_enabled()
    create_n = n + 1 if use_create else n
    raw = io.read_line(f"\n  เลือกโลก (1–{create_n} · 0=ย้อนกลับ): ").strip()
    if raw in ("", "0", "q", "Q"):
        io.write_line("  ย้อนกลับเมนูหลัก")
        return None
    try:
        idx = int(raw)
    except Exception:
        io.write_line(f"  เลขไม่ถูกต้อง — พิมพ์ 1–{create_n} หรือ 0 ย้อนกลับ")
        return None
    if use_create and idx == create_n:
        return run_create_world_flow(reg, io)
    if 1 <= idx <= n:
        return str(rows[idx - 1]["id"])
    io.write_line(f"  นอกช่วง — พิมพ์ 1–{create_n} หรือ 0 ย้อนกลับ")
    return None


def prepare_player_for_world(
    player: Dict[str, Any],
    reg: DataRegistry,
    world_id: str,
    *,
    new_character: bool = False,
) -> List[str]:
    """
    Stamp world mods + theme.
    new_character=True → seed mastery/skill once and set start area.
    Load existing → seed only if never applied (legacy migrate once).
    """
    return apply_world_theme_to_player(
        player,
        reg,
        world_id=world_id,
        force_seed=bool(new_character),
    )

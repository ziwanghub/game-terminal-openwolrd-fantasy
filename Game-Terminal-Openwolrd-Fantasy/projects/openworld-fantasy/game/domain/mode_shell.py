"""
Mode Shell — UX modes for terminal play (docs/MODE_SHELL_DESIGN.md).

Phase A: EXPLORE short menu + PERSONAL hub entry.
Combat/Shop still use their own loops; chrome labels align.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

# Canonical mode ids
MODE_EXPLORE = "explore"
MODE_PERSONAL = "personal"
MODE_COMBAT = "combat"
MODE_SHOP = "shop"
MODE_DUNGEON = "dungeon"  # explore variant chrome

MODE_LABELS = {
    MODE_EXPLORE: "สำรวจ",
    MODE_PERSONAL: "ตัวละคร",
    MODE_COMBAT: "ไฟต์",
    MODE_SHOP: "ร้าน",
    MODE_DUNGEON: "ดันเจียน",
}


def mode_label(mode: str) -> str:
    return MODE_LABELS.get(str(mode or ""), str(mode or "?"))


def render_mode_actions(
    mode: str,
    *,
    stat_points: int = 0,
    personality_points: int = 0,
    boss_line: str = "",
    mission_line: str = "",
    money_world: Optional[int] = None,
) -> str:
    """Short action block for the active mode (≤ ~8 option lines)."""
    m = str(mode or MODE_EXPLORE).lower()
    if m == MODE_PERSONAL:
        return _personal_actions(
            stat_points=stat_points,
            personality_points=personality_points,
            mission_line=mission_line,
            money_world=money_world,
        )
    if m == MODE_COMBAT:
        return _combat_actions()
    if m == MODE_SHOP:
        return _shop_actions()
    if m == MODE_DUNGEON:
        return _dungeon_actions_hint()
    return _explore_actions(
        stat_points=stat_points,
        personality_points=personality_points,
        boss_line=boss_line,
    )


def _explore_actions(
    *,
    stat_points: int,
    personality_points: int,
    boss_line: str,
) -> str:
    """
    Action panel — three bands: หลัก / ระบบ / ออก
    Returned as plain lines (caller may wrap in box).
    """
    from game.ui_terminal.layout import render_box

    lines: List[str] = [
        " ทำอะไรต่อ",
        "---",
        " หลัก",
        "  1  พัก        2  สำรวจ       3  เข้าหา",
        "  4  เดินทาง    5  ตัวละคร(I)  6  ร้าน/คราฟ",
        "---",
        " ระบบ",
        "  7  ออโต้   B  บอส   G  ขอแรง   H  ช่วย   T  บทเรียน",
        "  A  อันดับ/ท้า   P  แต้มสถานะ   N  แต้มนิสัย   S  สถานะ",
        "---",
        "  0  ออก (เซฟ)",
    ]
    if boss_line:
        bl = str(boss_line).strip()
        if not bl.startswith("☠") and "บอส" not in bl:
            bl = f"☠ {bl}"
        lines.append("---")
        lines.append(f" {bl}")
    if stat_points > 0 or personality_points > 0:
        lines.append("---")
        bits = []
        if stat_points > 0:
            bits.append(f"แต้มสถานะ {stat_points} → P")
        if personality_points > 0:
            bits.append(f"แต้มนิสัย {personality_points} → N")
        lines.append(" ✦ " + "  ·  ".join(bits))
    # keep marker for tests that search "ทำอะไรต่อ"
    return render_box(lines, double=False)


def _personal_actions(
    *,
    stat_points: int,
    personality_points: int,
    mission_line: str,
    money_world: Optional[int],
) -> str:
    """
    Menu-only block (no vitals/money/points dump — hub frame owns those).
    Still accepts money_world for API compat; unused when embedded in hub.
    """
    from game.ui_terminal.layout import render_box

    lines: List[str] = [
        " เมนูตัวละคร",
        "---",
        " ดูแล",
        "  R  พักดูแล      E  กินเสบียง",
        "---",
        " จัดการ",
        "  1  สถานะเต็ม     2  กระเป๋า      3  เกียร์",
        "  4  ภารกิจ        5  เงินย่อ      6  แต้ม P/N/C",
        "  7  สกิล·ปาร์ตี้·ห้องสมุด",
        "  8  ตั้งค่า/เซฟ",
        "---",
        "  0  กลับสำรวจ",
    ]
    if mission_line:
        lines.append("---")
        lines.append(f" {str(mission_line).strip()}")
    if stat_points > 0 or personality_points > 0:
        lines.append("---")
        bits = []
        if stat_points > 0:
            bits.append(f"แต้มสถานะ {stat_points} → P (หรือ 6)")
        if personality_points > 0:
            bits.append(f"แต้มนิสัย {personality_points} → N (หรือ 6)")
        lines.append(" ✦ " + "  ·  ".join(bits))
    # money_world kept out of menu to avoid dup with status frame
    _ = money_world
    return render_box(lines, double=False)


def _combat_actions() -> str:
    from game.ui_terminal.layout import render_box

    return render_box(
        [
            " ไฟต์ · คำสั่ง",
            "---",
            " โจมตี",
            "  1  โจมตีปกติ      2  สกิล / คอมโบ",
            "---",
            " ช่วยเหลือ",
            "  3  ยา / ล้าง / บัฟ",
            "  5  ปาร์ตี้         6  สติเร่งจังหวะ",
            "---",
            "  4  หนี           7  เจรจา soft (บางศัตรู)",
            "---",
            " (แท่งจังหวะเต็มก่อนเลือก · เจรจาได้ครั้งเดียวต่อไฟต์)",
        ],
        double=False,
    )


def _shop_actions() -> str:
    from game.ui_terminal.layout import render_box

    return render_box(
        [
            " โหมดร้าน",
            "---",
            " ร้านระบบ",
            "  1  ร้านท้องถิ่น          ของใช้ทั่วไป",
            "  2  ตลาดสวรรค์ / นรก      สกุลเงินพิเศษ",
            "  3  ตลาดหายาก / ศาลา      วัสดุ · รับซื้อแรงก์สูง",
            "---",
            " ผู้เล่น · อื่น",
            "  4 / M  ตลาดผู้เล่น        ตั้งราคา · ภาษี",
            "  5      คราฟ",
            "  6      ดูเงินย่อ",
            "---",
            "  0  กลับสำรวจ",
            "---",
            " ในร้าน: 1 ซื้อ → เลือกหมวด → เลือกชิ้น",
        ],
        double=False,
    )


def _dungeon_actions_hint() -> str:
    return "\n".join(
        [
            "── ดันเจียน ──",
            " ใช้เมนูดันเจียนบนจอ · Y ปาร์ตี้ · 0 ออกเมื่อปลดล็อก",
        ]
    )


def active_mission_line(player: Mapping[str, Any]) -> str:
    """One soft line for PERSONAL header."""
    bm = player.get("board_mission")
    if isinstance(bm, dict) and bm.get("name"):
        return f" กระดาน: {bm.get('name')} ({bm.get('rank') or '?'})"
    qstate = player.get("quests") or {}
    active = [qid for qid, st in qstate.items() if not (st or {}).get("completed")]
    if active:
        return f" เควสโลกค้าง ~{len(active)} สาย"
    return ""


def money_summary_lines(player: Mapping[str, Any]) -> List[str]:
    lines = [
        " เงิน / เศรษฐกิจย่อ",
        "---",
        f" โลก {int(player.get('money_world') or 0)} · "
        f"สวรรค์ {int(player.get('money_heaven') or 0)} · "
        f"นรก {int(player.get('money_hell') or 0)}",
    ]
    inbox = player.get("market_inbox") or []
    if inbox:
        lines.append(f" กล่องตลาด: {len(inbox)} รายการ (เปิดตลาด M ในกระเป๋า)")
    else:
        lines.append(" กล่องตลาด: ว่าง")
    rank = player.get("mission_rank") or "F"
    lines.append(f" แรงก์กระดาน: {rank}")
    return lines

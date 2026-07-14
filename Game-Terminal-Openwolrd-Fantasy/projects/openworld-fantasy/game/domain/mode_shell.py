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
    lines: List[str] = ["── สำรวจ · ทำอะไรต่อ ──"]
    if boss_line:
        lines.append(boss_line)
    lines.extend(
        [
            " 1 พัก   2 สำรวจ   3 เข้าหา   4 เดินทาง",
            " 5 / I  ตัวละคร   6 ร้าน/ตลาด/คราฟ",
            " 7 ออโต้   B บอส   H ช่วย   T บทเรียน   0 ออก(เซฟ)",
            " คำสั่ง: f_mn01 · o_ · talk_ · ?  |  hotkey P/S/… ยังใช้ได้",
        ]
    )
    if stat_points > 0:
        lines.append(f" ✦ แต้มสถานะค้าง {stat_points} — กด I แล้ว 6 หรือ P")
    if personality_points > 0:
        lines.append(f" ✦ แต้มนิสัย {personality_points} — กด I แล้ว 6 หรือ N")
    return "\n".join(lines)


def _personal_actions(
    *,
    stat_points: int,
    personality_points: int,
    mission_line: str,
    money_world: Optional[int],
) -> str:
    lines: List[str] = ["── ตัวละคร (PERSONAL) ──"]
    if money_world is not None:
        lines.append(f" เงินโลก {money_world}")
    if mission_line:
        lines.append(mission_line)
    lines.extend(
        [
            " 1 สถานะเต็ม   2 กระเป๋า(ของ)   3 สวมใส่/เกียร์",
            " 4 ภารกิจ   5 เงินย่อ   6 แต้ม P/N/C",
            " 7 สกิล·ปาร์ตี้·ห้องสมุด   8 ตั้งค่า/เซฟ",
            " ร้าน/ตลาด → กลับสำรวจแล้วกด 6   |   0 กลับสำรวจ",
        ]
    )
    if stat_points > 0:
        lines.append(f" ✦ แต้มสถานะ {stat_points} — เลือก 6 แล้ว P")
    if personality_points > 0:
        lines.append(f" ✦ แต้มนิสัย {personality_points} — เลือก 6 แล้ว N")
    return "\n".join(lines)


def _combat_actions() -> str:
    return "\n".join(
        [
            "── ไฟต์ · คำสั่ง (แท่งเต็ม) ──",
            " 1 โจมตี   2 สกิล/คอมโบ   3 ยา/ล้าง/บัฟ",
            " 4 หนี   5 ปาร์ตี้   6 สติเร่งจังหวะ",
            " (ไม่เปิดตัวละคร/ร้านในไฟต์)",
        ]
    )


def _shop_actions() -> str:
    return "\n".join(
        [
            "── ร้าน (SHOP) ──",
            " 1 ร้านท้องถิ่น   2 ตลาดสวรรค์/นรก   3 ตลาดหายาก/ตำนาน",
            " 4 / M  ตลาดผู้เล่น   5 คราฟ   6 ดูเงินย่อ   0 กลับสำรวจ",
        ]
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
        "── เงิน / เศรษฐกิจย่อ ──",
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

"""
Mode Shell — UX modes for terminal play (docs/MODE_SHELL_DESIGN.md).

Phase A: EXPLORE short menu + PERSONAL hub entry.
Combat/Shop still use their own loops; chrome labels align.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence  # Any for optional reg

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
    player: Optional[Mapping[str, Any]] = None,
    reg: Any = None,
) -> str:
    """Short action block for the active mode (≤ ~8 option lines)."""
    m = str(mode or MODE_EXPLORE).lower()
    if m == MODE_PERSONAL:
        return _personal_actions(
            stat_points=stat_points,
            personality_points=personality_points,
            mission_line=mission_line,
            money_world=money_world,
            player=player,
            reg=reg,
        )
    if m == MODE_COMBAT:
        return _combat_actions(player=player, reg=reg)
    if m == MODE_SHOP:
        return _shop_actions()
    if m == MODE_DUNGEON:
        return _dungeon_actions_hint()
    return _explore_actions(
        stat_points=stat_points,
        personality_points=personality_points,
        boss_line=boss_line,
        player=player,
        reg=reg,
    )


def _care_stock_and_oneliner(
    player: Optional[Mapping[str, Any]],
    reg: Any,
) -> tuple:
    """Shared care band stock counts + Auto Policy oneliner."""
    food_n, hp_n, mp_n = "?", "?", "?"
    a_line = "สรุป agent"
    if player is not None and reg is not None:
        try:
            from game.runtime.dungeon_auto import count_food, count_potions
            from game.services.auto_policy_hub import care_auto_oneliner

            food_n = str(count_food(player, reg))
            hp_n = str(count_potions(player, reg, kind="hp"))
            mp_n = str(count_potions(player, reg, kind="mp"))
            a_line = care_auto_oneliner(player, reg)  # type: ignore[arg-type]
        except Exception:
            pass
    elif player is not None:
        try:
            from game.domain.needs import soft_label, get_needs
            from game.services.auto_policy_hub import _morale_menu_bit

            n = get_needs(player)
            a_line = (
                f"{_morale_menu_bit(soft_label('morale', int(n['morale'])))} · "
                f"ล้า{soft_label('fatigue', int(n['fatigue']))}"
            )
        except Exception:
            pass
    return food_n, hp_n, mp_n, a_line


def _explore_actions(
    *,
    stat_points: int,
    personality_points: int,
    boss_line: str,
    player: Optional[Mapping[str, Any]] = None,
    reg: Any = None,
) -> str:
    """
    Action panel — bands: หลัก / ดูแล & Auto Play / ระบบ / ออก
    Field: H/M = care potions · O = Auto Policy · A = rank · ? = help
    """
    from game.ui_terminal.layout import render_box

    food_n, hp_n, mp_n, a_line = _care_stock_and_oneliner(player, reg)

    lines: List[str] = [
        " ทำอะไรต่อ",
        "---",
        " หลัก",
        "  1  พัก        2  สำรวจ       3  เข้าหา",
        "  4  เดินทาง    5  ตัวละคร(I)  6  ร้าน/คราฟ",
        "  U  ลานอารีน่า (เมือง/ยอดผลึก · ทีม 1–4 · 3 รอบ)",
        "---",
        " 【ดูแล & Auto Play】",
        "  R  พักเต็ม",
        f"  E  กินเสบียง          [อาหาร {food_n}]",
        f"  H  ยาเพิ่มเลือด       [HP {hp_n}]",
        f"  M  ยาเพิ่มมานา       [MP {mp_n}]",
        f"  O  ตั้ง Auto Policy   ({a_line})",
        "---",
        " ระบบ",
        "  7  ออโต้   B  บอส   G  ขอแรง   ?  ช่วย   T  บทเรียน",
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
    player: Optional[Mapping[str, Any]] = None,
    reg: Any = None,
) -> str:
    """
    WO-009: Care & Auto Play on top with stock counts + A oneliner.
    Index 1–6 below. money_world unused (hub frame owns money).
    """
    from game.ui_terminal.layout import render_box

    food_n, hp_n, mp_n, a_line = _care_stock_and_oneliner(player, reg)

    # pad counts for alignment (terminal-friendly)
    lines: List[str] = [
        " เมนูตัวละคร",
        "---",
        " 【ดูแล & Auto Play】",
        "  R  พักเต็ม",
        f"  E  กินเสบียง          [อาหาร {food_n}]",
        f"  H  ยาเพิ่มเลือด       [HP {hp_n}]",
        f"  M  ยาเพิ่มมานา       [MP {mp_n}]",
        f"  A  ตั้ง Auto Policy   ({a_line})",
        "  X  Test Run (Playtest)",
        "---",
        "  1  สถานะโดยรวม",
        "  2  กระเป๋า / อุปกรณ์",
        "  3  สกิล",
        "  4  นิสัย / ฉายา",
        "  5  ปาร์ตี้ / สัมพันธ์",
        "  6  ประวัติ / Log",
        "---",
        "  7  ภารกิจ   8  ตั้งค่า/เซฟ   9  เงิน·ห้องสมุด",
        "---",
        "  0  กลับ",
    ]
    # WO-011: show God compact / last run hint when active
    try:
        from game.runtime.auto_run_log import is_god_compact

        if player is not None and is_god_compact(player):
            lines.append("---")
            lines.append(" ✦ God Compact เปิด · กายใจ+Policy เด่นตอน Auto")
    except Exception:
        pass

    if mission_line:
        lines.append("---")
        lines.append(f" {str(mission_line).strip()}")
    if stat_points > 0 or personality_points > 0:
        lines.append("---")
        bits = []
        if stat_points > 0:
            bits.append(f"แต้มสถานะ {stat_points} → 4 หรือ P")
        if personality_points > 0:
            bits.append(f"แต้มนิสัย {personality_points} → 4 หรือ N")
        lines.append(" ✦ " + "  ·  ".join(bits))
    _ = money_world
    return render_box(lines, double=False)


def combat_auto_play_soft_hints(player: Optional[Mapping[str, Any]]) -> List[str]:
    """WO-010: soft hints when Needs pressure — nudge Auto Play."""
    if player is None:
        return []
    try:
        from game.domain.needs import band, get_needs

        n = get_needs(player)
        out: List[str] = []
        mb = band("morale", int(n["morale"]))
        fb = band("fatigue", int(n["fatigue"]))
        if mb in ("low", "crit"):
            out.append("…ขวัญหด — แนะนำ Auto Play ด้วย Caution")
        if fb in ("bad", "crit"):
            out.append("…ร่างกายอ่อนล้า — Auto Play อาจช่วยจัดการ")
        return out[:2]
    except Exception:
        return []


def _combat_actions(
    player: Optional[Mapping[str, Any]] = None,
    reg: Any = None,
) -> str:
    """
    Combat command band — keep 1–7; WO-010 adds 8 / A Auto Play.
    Soft needs hints when player is stressed.
    """
    from game.ui_terminal.layout import render_box

    lines: List[str] = [
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
        " Auto Play",
        "  8  Auto Play     A  (ลัด · Continuous/Step + สรุปไฟต์)",
        "---",
        " (Continuous รันจนรู้ผล · Step=Enter ทีละจังหวะ · แพ้=Soft Death)",
    ]
    for h in combat_auto_play_soft_hints(player):
        lines.append(f" {h}")
    _ = reg
    return render_box(lines, double=False)



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

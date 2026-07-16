"""
WO-008: Auto Policy Hub — single place for auto_prefs + inv_* + soft agent summary.
Opened from personal menu with A (not field A=rank).
"""
from __future__ import annotations

from typing import Any, Dict, List, MutableMapping

from game.data_load.registry import DataRegistry
from game.domain.needs import band, get_needs, soft_label
from game.ports.io import IO
from game.ui_terminal.layout import render_box


def _morale_menu_bit(mor_label: str) -> str:
    """soft_label high is already 'ขวัญดี' — do not prefix ขวัญ again."""
    lab = str(mor_label or "").strip()
    if not lab:
        return "ขวัญ?"
    if lab.startswith("ขวัญ"):
        return lab
    return f"ขวัญ{lab}"


def care_auto_oneliner(player: MutableMapping[str, Any], reg: DataRegistry) -> str:
    """
    WO-009: one short line for menu next to A/O.
    e.g. ขวัญหด · ล้า → Caution   |   ขวัญดี · ล้าเบา → Caution
    """
    from game.runtime.dungeon_auto import ensure_auto_prefs

    prefs = ensure_auto_prefs(player)
    n = get_needs(player)
    hun = soft_label("hunger", int(n["hunger"]))
    fat = soft_label("fatigue", int(n["fatigue"]))
    mor = soft_label("morale", int(n["morale"]))
    pol = str(prefs.get("low_morale_policy") or "caution")
    pol_disp = {"ignore": "Ignore", "caution": "Caution", "retreat": "Retreat"}.get(
        pol, pol.title()
    )
    # lead with stressed axes
    bits: List[str] = []
    mb = band("morale", int(n["morale"]))
    fb = band("fatigue", int(n["fatigue"]))
    hb = band("hunger", int(n["hunger"]))
    # soft_label may already embed axis (ขวัญดี) — prefix only when needed
    if mb in ("low", "crit"):
        bits.append(_morale_menu_bit(mor))
    if fb in ("bad", "crit"):
        bits.append(f"ล้า·{fat}" if fat != "ล้า" else "ล้า")
    if hb in ("bad", "crit"):
        bits.append(f"หิว·{hun}" if hun not in ("หิว", "อดอยาก") else hun)
    if not bits:
        bits.append(_morale_menu_bit(mor))
        bits.append(fat if fat != "เบา" else "ล้าเบา")
    return f"{' · '.join(bits[:2])} → {pol_disp}"


def soft_agent_summary(player: MutableMapping[str, Any], reg: DataRegistry) -> List[str]:
    """What the agent will likely do — soft language, no formulas."""
    from game.runtime.dungeon_auto import ensure_auto_prefs, _effective_thresholds

    prefs = ensure_auto_prefs(player)
    th = _effective_thresholds(player, reg)
    n = get_needs(player)
    hun, fat, mor = int(n["hunger"]), int(n["fatigue"]), int(n["morale"])
    lines = [
        " Agent จะทำอะไร (สรุป soft)",
        "---",
        f" ตอนนี้  หิว {soft_label('hunger', hun)} · "
        f"ล้า {soft_label('fatigue', fat)} · "
        f"ขวัญ {soft_label('morale', mor)}",
        f" สรุป   {care_auto_oneliner(player, reg)}",
        "---",
        f" กินเมื่อ  หิว ≥ {th.get('hunger')}   ·  พักเมื่อ  ล้า ≥ {th.get('fatigue')}",
        f" ยา HP เมื่อ ≤ {th.get('hp_pct')}%   ·  ยา MP เมื่อ ≤ {th.get('mp_pct')}%",
        f" ขวัญดูแล ≤ {th.get('morale', prefs.get('morale'))}   ·  "
        f"นโยบาย {prefs.get('low_morale_policy')}",
    ]
    pol = str(prefs.get("low_morale_policy") or "caution")
    mb = band("morale", mor)
    if pol == "ignore":
        lines.append(" · ขวัญ: ไม่เลี่ยงไฟต์จากขวัญ")
    elif mb in ("low", "crit") or mor <= int(th.get("morale") or 35):
        if pol == "retreat":
            lines.append(" · ขวัญต่ำ → อาจหยุดออโต้ (retreat)")
        else:
            lines.append(" · ขวัญต่ำ → เลี่ยงไฟต์ · ลดความก้าวร้าว · อาจพัก/กิน")
    else:
        lines.append(" · ขวัญพอ → ต่อสู้ตามปกติ (caution เมื่อขวัญตก)")

    if prefs.get("inv_manage", True):
        junk = (
            "ขายขยะ"
            if prefs.get("inv_sell_junk", True)
            else ("ทิ้งขยะ" if prefs.get("inv_drop_junk") else "ขยะปิด")
        )
        buy = "เปิด" if prefs.get("auto_buy_supplies") else "ปิด"
        lines.append(
            f" · กระเป๋า: อาหาร<{prefs.get('inv_min_food')} · {junk} · "
            f"ซื้อเสบียง={buy}"
        )
    plan = prefs.get("skill_plan") or [1]
    lines.append(f" · แผนสกิลดัน: {plan}")
    lines.append("---")
    mode = str(prefs.get("item_mode") or "normal")
    lines.append(" โหมดของ: " + mode)
    # WO-022: soft economy hint by item_mode
    if prefs.get("auto_buy_supplies"):
        if mode == "thrift":
            lines.append(" · ซื้อ: thrift → สำรองสูง · ซื้อทีละ 1")
        elif mode == "safe":
            lines.append(" · ซื้อ: safe → สำรองต่ำ · เติมเสบียงถี่ขึ้น")
        else:
            lines.append(
                f" · ซื้อ: normal · สำรอง {prefs.get('auto_buy_reserve', 50)}G"
            )
    # WO-023/025 burden + echo policy
    try:
        from game.domain.divine_burden import burden_summary_for_log

        lines.append(
            f" · {burden_summary_for_log(player, reg)} · "
            f"ถอดภาระ={'เปิด' if prefs.get('auto_unequip_burden', True) else 'ปิด'}"
        )
    except Exception:
        lines.append(
            f" · ถอดภาระเรลิก="
            f"{'เปิด' if prefs.get('auto_unequip_burden', True) else 'ปิด'}"
        )
    lines.append(
        f" · เลี่ยงเงาออร่า="
        f"{'เปิด' if prefs.get('auto_avoid_relic_echo', True) else 'ปิด'}"
    )
    return lines


def run_auto_policy_hub(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
) -> None:
    """Interactive hub — edit prefs + show agent summary."""
    from game.runtime.dungeon_auto import (
        ensure_auto_prefs,
        skill_plan_labels,
        list_combat_skill_ids,
        _parse_skill_plan_str,
    )
    from game.runtime.inventory_auto import ensure_inv_auto_prefs, format_inv_auto_hud

    ensure_inv_auto_prefs(player)  # noqa: F841 — merge inv keys

    while True:
        prefs = ensure_auto_prefs(player)
        io.write_line()
        io.write_line(render_box(soft_agent_summary(player, reg), double=False))
        io.write_line()
        io.write_line(f"  {format_inv_auto_hud(player, reg)}")
        menu = [
            " Auto Policy Hub",
            "---",
            f" 1  HP ใช้ยา ≤ {prefs['hp_pct']}%",
            f" 2  MP ใช้ยา ≤ {prefs['mp_pct']}%",
            f" 3  หิว กิน ≥ {prefs['hunger']}",
            f" 4  ล้า พัก ≥ {prefs['fatigue']}",
            f" 5  ขวัญ ดูแล ≤ {prefs['morale']}",
            f" 6  นโยบายขวัญ: {prefs['low_morale_policy']}  (ignore/caution/retreat)",
            f" 7  โหมดของ: {prefs['item_mode']}  (thrift/normal/safe)",
            f" 8  แผนสกิล: {prefs['skill_plan']} = "
            f"{skill_plan_labels(player, reg, prefs['skill_plan'])}",
            f" 9  กระเป๋า: manage={prefs.get('inv_manage')} "
            f"ขายขยะ={prefs.get('inv_sell_junk', True)} "
            f"ทิ้ง={prefs.get('inv_drop_junk')} "
            f"minอาหาร={prefs.get('inv_min_food')}",
            f" A  ซื้อเสบียงอัตโนมัติ: "
            f"{'เปิด' if prefs.get('auto_buy_supplies') else 'ปิด'} "
            f"(สำรอง {prefs.get('auto_buy_reserve', 40)}G · "
            f"สูงสุด {prefs.get('auto_buy_max', 2)}/รอบ)",
            f" B  ภาระ/ออร่า: ถอดภาระ="
            f"{'เปิด' if prefs.get('auto_unequip_burden', True) else 'ปิด'} · "
            f"เลี่ยงเงาออร่า="
            f"{'เปิด' if prefs.get('auto_avoid_relic_echo', True) else 'ปิด'}",
            "---",
            " 0  กลับ",
        ]
        io.write_line(render_box(menu, double=False))
        ch = io.read_line("\n  Auto Policy> ").strip().lower()
        if ch in ("0", "", "q"):
            return
        if ch == "1":
            raw = io.read_line(f"  HP% (15-70) [{prefs['hp_pct']}]: ").strip()
            if raw.isdigit():
                prefs["hp_pct"] = int(raw)
        elif ch == "2":
            raw = io.read_line(f"  MP% (5-50) [{prefs['mp_pct']}]: ").strip()
            if raw.isdigit():
                prefs["mp_pct"] = int(raw)
        elif ch == "3":
            raw = io.read_line(f"  หิว (25-85) [{prefs['hunger']}]: ").strip()
            if raw.isdigit():
                prefs["hunger"] = int(raw)
        elif ch == "4":
            raw = io.read_line(f"  ล้า (30-90) [{prefs['fatigue']}]: ").strip()
            if raw.isdigit():
                prefs["fatigue"] = int(raw)
        elif ch == "5":
            raw = io.read_line(f"  ขวัญ (10-70) [{prefs['morale']}]: ").strip()
            if raw.isdigit():
                prefs["morale"] = int(raw)
        elif ch == "6":
            raw = io.read_line("  ignore / caution / retreat: ").strip().lower()
            if raw in ("ignore", "caution", "retreat", "i", "c", "r"):
                prefs["low_morale_policy"] = {
                    "i": "ignore",
                    "c": "caution",
                    "r": "retreat",
                }.get(raw, raw)
        elif ch == "7":
            raw = io.read_line("  thrift / normal / safe: ").strip().lower()
            if raw in ("thrift", "normal", "safe", "t", "n", "s"):
                prefs["item_mode"] = {
                    "t": "thrift",
                    "n": "normal",
                    "s": "safe",
                }.get(raw, raw)
        elif ch == "8":
            skills = list_combat_skill_ids(player, reg)
            for i, sid in enumerate(skills, 1):
                if sid == "__basic__":
                    io.write_line(f"   {i}. โจมตีปกติ")
                else:
                    nm = (reg.skills.get(sid) or {}).get("name") or sid
                    io.write_line(f"   {i}. {nm}")
            raw = io.read_line("  แผน เช่น 2 1 3 (เว้นวรรค): ").strip()
            plan = _parse_skill_plan_str(raw)
            if plan:
                prefs["skill_plan"] = plan
        elif ch == "9":
            t = io.read_line(
                "  1 เปิด/ปิด manage  2 เปิด/ปิดขายขยะ  "
                "3 เปิด/ปิดทิ้งขยะ  4 ตั้ง min อาหาร: "
            ).strip()
            if t == "1":
                prefs["inv_manage"] = not bool(prefs.get("inv_manage", True))
            elif t == "2":
                prefs["inv_sell_junk"] = not bool(prefs.get("inv_sell_junk", True))
            elif t == "3":
                prefs["inv_drop_junk"] = not bool(prefs.get("inv_drop_junk", True))
            elif t == "4":
                raw = io.read_line(
                    f"  min อาหาร (0-12) [{prefs.get('inv_min_food', 2)}]: "
                ).strip()
                if raw.isdigit():
                    prefs["inv_min_food"] = int(raw)
        elif ch == "a":
            t = io.read_line(
                "  1 เปิด/ปิดซื้อเสบียง  2 สำรองเงิน  3 สูงสุด/รอบ: "
            ).strip()
            if t == "1":
                prefs["auto_buy_supplies"] = not bool(
                    prefs.get("auto_buy_supplies", False)
                )
            elif t == "2":
                raw = io.read_line(
                    f"  สำรองเงินโลก (0-500) [{prefs.get('auto_buy_reserve', 40)}]: "
                ).strip()
                if raw.isdigit():
                    prefs["auto_buy_reserve"] = int(raw)
            elif t == "3":
                raw = io.read_line(
                    f"  ซื้อสูงสุด/รอบ (0-6) [{prefs.get('auto_buy_max', 2)}]: "
                ).strip()
                if raw.isdigit():
                    prefs["auto_buy_max"] = int(raw)
        elif ch == "b":
            t = io.read_line(
                "  1 เปิด/ปิดถอดภาระเรลิก  2 เปิด/ปิดเลี่ยงเงาออร่า: "
            ).strip()
            if t == "1":
                prefs["auto_unequip_burden"] = not bool(
                    prefs.get("auto_unequip_burden", True)
                )
            elif t == "2":
                prefs["auto_avoid_relic_echo"] = not bool(
                    prefs.get("auto_avoid_relic_echo", True)
                )
        player["auto_prefs"] = prefs
        ensure_auto_prefs(player)
        ensure_inv_auto_prefs(player)

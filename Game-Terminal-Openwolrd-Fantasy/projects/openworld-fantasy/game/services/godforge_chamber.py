"""
WO-023.3 Godforge Chamber / ห้องทดสอบเรลิก

Sandbox: loan chamber relics, spar, measure power vs burden.
Exit returns all loaned gear — never farms world money.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, MutableMapping, Optional

from game.data_load.registry import DataRegistry
from game.ports.io import IO
from game.ui_terminal.layout import render_box

# Synthetic chamber-only templates (not added to world bag permanently)
CHAMBER_RELICS: List[Dict[str, Any]] = [
    {
        "id": "chamber_blade_storm",
        "name": "ดาบทดสอบ · วายุเทพ",
        "kind": "equipment",
        "slot": "main_hand",
        "rarity": "legendary",
        "atk": 28,
        "chamber_relic": True,
        "force_burden": True,
        "desc": "เรลิกยืมจากห้อง — สายลมกดจิต",
    },
    {
        "id": "chamber_blade_hell",
        "name": "ดาบทดสอบ · นรกดำ",
        "kind": "equipment",
        "slot": "main_hand",
        "rarity": "divine",
        "atk": 36,
        "chamber_relic": True,
        "force_burden": True,
        "desc": "เรลิกยืม — ความร้อนแผ่จากคม",
    },
    {
        "id": "chamber_mail_aegis",
        "name": "เกราะทดสอบ · เกราะสวรรค์",
        "kind": "equipment",
        "slot": "body",
        "rarity": "legendary",
        "def": 22,
        "max_hp": 40,
        "chamber_relic": True,
        "force_burden": True,
        "desc": "เรลิกยืม — หนักแต่คุ้มครอง",
    },
    {
        "id": "chamber_ring_void",
        "name": "แหวนทดสอบ · สุญญะ",
        "kind": "equipment",
        "slot": "acc_1",
        "rarity": "legendary",
        "atk": 8,
        "max_mana": 20,
        "chamber_relic": True,
        "force_burden": True,
        "desc": "เรลิกยืม — เงียบจนน่ากลัว",
    },
]


def _session(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    raw = player.get("godforge_session")
    if isinstance(raw, dict) and raw.get("active"):
        return raw
    return {}


def in_godforge(player: MutableMapping[str, Any]) -> bool:
    return bool(_session(player).get("active"))


def _inject_chamber_items(reg: DataRegistry) -> None:
    """Register chamber templates into reg.items for equip/display (session only)."""
    items = reg.items
    if items is None:
        return
    for row in CHAMBER_RELICS:
        iid = str(row["id"])
        if iid not in items:
            items[iid] = dict(row)


def enter_godforge(player: MutableMapping[str, Any], reg: DataRegistry) -> List[str]:
    """Start chamber session — snapshot equip, clear loans."""
    if in_godforge(player):
        return ["  อยู่ในห้องทดสอบเรลิกอยู่แล้ว"]
    _inject_chamber_items(reg)
    snap = {
        "equip_ids": dict(player.get("equip_ids") or {}),
        "equip_rarities": dict(player.get("equip_rarities") or {}),
        "money_world": int(player.get("money_world") or 0),
        "money_heaven": int(player.get("money_heaven") or 0),
        "money_hell": int(player.get("money_hell") or 0),
        "hp": int(player.get("hp") or 0),
        "mp": int(player.get("mp") or player.get("mana") or 0),
    }
    from game.domain.needs import ensure_needs, get_needs

    ensure_needs(player)
    mor0 = int(get_needs(player).get("morale") or 50)
    player["godforge_session"] = {
        "active": True,
        "mode": "burden",  # burden | power
        "loaned": [],  # item ids currently loaned into inventory/equip
        "snapshot": snap,
        "burden_muted": False,
        "spar_count": 0,
        "morale_enter": mor0,
        "log": [],  # short session notes for summary
    }
    player.pop("burden_muted", None)
    notes = [
        "── เข้า ห้องทดสอบเรลิก (Godforge Chamber) ──",
        "  ของที่ยืมใช้ได้เฉพาะในห้อง · ออกแล้วคืนทั้งหมด",
        "  ไม่ได้เงินโลกจากการซ้อมในนี้",
        "  โหมดเริ่ม: วัดภาระ (Burden เปิด)",
        "  ใบ้: 2 ยืม → 5 ใส่ → 4 spar (แรงขึ้น) · 3 โหมด · 7 สรุปภาระ · 6 ออก",
        "  ใบ้: วัดภาระ = รู้สึกขวัญ · วัดพลัง = ปิดโทษชั่วคราว",
    ]
    if not player.get("_godforge_seen_tip"):
        player["_godforge_seen_tip"] = True
        notes.append("  (ครั้งแรก) ห้องนี้เพื่อลองของเทพโดยไม่พังเซฟโลก")
    # WO-038: divine-leaning world presence
    try:
        from game.domain.world_relations import on_chamber_enter

        notes.extend(on_chamber_enter(player))
    except Exception:
        pass
    return notes


def set_chamber_mode(
    player: MutableMapping[str, Any],
    mode: str,
) -> List[str]:
    sess = _session(player)
    if not sess.get("active"):
        return ["  ยังไม่ได้อยู่ในห้องทดสอบ"]
    m = str(mode or "burden").lower()
    if m in ("power", "p", "วัดพลัง", "measure"):
        sess["mode"] = "power"
        sess["burden_muted"] = True
        player["godforge_session"] = sess
        player["burden_muted"] = True
        return ["  โหมด: วัดพลัง — ภาระเรลิกปิดชั่วคราว"]
    sess["mode"] = "burden"
    sess["burden_muted"] = False
    player["godforge_session"] = sess
    player.pop("burden_muted", None)
    return ["  โหมด: วัดภาระ — ภาระเรลิกเปิดเหมือนโลกจริง"]


def loan_relic(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    relic_id: str,
) -> List[str]:
    _inject_chamber_items(reg)
    sess = _session(player)
    if not sess.get("active"):
        return ["  ยังไม่ได้อยู่ในห้องทดสอบ"]
    row = next((r for r in CHAMBER_RELICS if r["id"] == relic_id), None)
    if not row:
        return ["  ไม่พบเรลิกทดลองนั้น"]
    loaned = list(sess.get("loaned") or [])
    if relic_id in loaned:
        return ["  ยืมชิ้นนี้แล้ว"]
    if len(loaned) >= 4:
        return ["  ยืมได้สูงสุด 4 ชิ้น"]
    # put in inventory as id
    ids = list(player.get("inventory_ids") or [])
    ids.append(relic_id)
    player["inventory_ids"] = ids
    rar = list(player.get("inventory_rarities") or [])
    while len(rar) < len(ids) - 1:
        rar.append("common")
    rar.append(str(row.get("rarity") or "legendary"))
    player["inventory_rarities"] = rar
    inv = list(player.get("inventory") or [])
    inv.append(str(row.get("name") or relic_id))
    player["inventory"] = inv
    loaned.append(relic_id)
    sess["loaned"] = loaned
    player["godforge_session"] = sess
    # ensure reg has item
    if relic_id not in (reg.items or {}):
        (reg.items or {})[relic_id] = dict(row)
    return [f"  ยืม「{row.get('name')}」แล้ว (ใส่จากกระเป๋าได้)"]


def _strip_loaned_from_player(player: MutableMapping[str, Any], loaned: List[str]) -> None:
    loaned_set = set(loaned)
    # unequip loaned
    eq = dict(player.get("equip_ids") or {})
    er = dict(player.get("equip_rarities") or {})
    for slot, iid in list(eq.items()):
        if str(iid) in loaned_set:
            eq[slot] = None
            er.pop(slot, None)
    # clean Nones
    player["equip_ids"] = {k: v for k, v in eq.items() if v}
    player["equip_rarities"] = er
    # bag
    ids = list(player.get("inventory_ids") or [])
    rars = list(player.get("inventory_rarities") or [])
    inv = list(player.get("inventory") or [])
    new_ids, new_rars, new_inv = [], [], []
    for i, iid in enumerate(ids):
        if str(iid) in loaned_set:
            continue
        new_ids.append(iid)
        if i < len(rars):
            new_rars.append(rars[i])
        if i < len(inv):
            new_inv.append(inv[i])
    player["inventory_ids"] = new_ids
    player["inventory_rarities"] = new_rars
    player["inventory"] = new_inv


def exit_godforge(player: MutableMapping[str, Any], reg: DataRegistry) -> List[str]:
    sess = _session(player)
    if not sess.get("active"):
        return ["  ไม่อยู่ในห้องทดสอบ"]
    loaned = list(sess.get("loaned") or [])
    # summary while still equipped with loans + session stats
    notes = format_chamber_burden_summary(player, reg)
    _strip_loaned_from_player(player, loaned)
    snap = dict(sess.get("snapshot") or {})
    # restore money if somehow changed (anti-farm)
    if "money_world" in snap:
        player["money_world"] = int(snap["money_world"])
    if "money_heaven" in snap:
        player["money_heaven"] = int(snap["money_heaven"])
    if "money_hell" in snap:
        player["money_hell"] = int(snap["money_hell"])
    # restore pre-chamber equip if we wiped loaned from equip only —
    # keep player's real equip; re-apply snapshot equip that wasn't chamber
    snap_eq = dict(snap.get("equip_ids") or {})
    # if player still has empty slots that had gear before and we removed only loans,
    # merge: prefer current non-chamber, fill from snap
    cur = dict(player.get("equip_ids") or {})
    for slot, iid in snap_eq.items():
        if iid and str(iid) not in set(loaned):
            if not cur.get(slot):
                cur[slot] = iid
    player["equip_ids"] = {k: v for k, v in cur.items() if v}
    er = dict(player.get("equip_rarities") or {})
    for slot, rar in dict(snap.get("equip_rarities") or {}).items():
        if player.get("equip_ids", {}).get(slot) and slot not in er:
            er[slot] = rar
    player["equip_rarities"] = er
    player.pop("godforge_session", None)
    player.pop("burden_muted", None)
    try:
        from game.domain.equipment import recompute_stats

        recompute_stats(player, reg)
    except Exception:
        pass
    notes.extend(
        [
            "── ออกจากห้องทดสอบเรลิก ──",
            f"  คืนเรลิกยืม {len(loaned)} ชิ้นแล้ว",
            "  เงินโลกไม่เปลี่ยนจากการซ้อมในห้อง",
        ]
    )
    return notes


def format_chamber_burden_summary(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
) -> List[str]:
    """WO-027: God-readable summary after testing in chamber."""
    sess = _session(player)
    lines = ["── สรุปทดสอบภาระ (ห้อง) ──"]
    try:
        from game.domain.divine_burden import (
            burden_summary_for_log,
            soft_burden_status_line,
            worst_burden_band,
        )
        from game.domain.needs import get_needs, soft_label

        lines.append(f"  {burden_summary_for_log(player, reg)}")
        sl = soft_burden_status_line(player, reg)
        if sl:
            lines.append(f"  {sl}")
        n = get_needs(player)
        mor = int(n.get("morale") or 0)
        mor0 = int(sess.get("morale_enter") or mor)
        lines.append(
            f"  ขวัญ  {soft_label('morale', mor0)} → {soft_label('morale', mor)}"
            f"  ({mor0}→{mor})"
        )
        spars = int(sess.get("spar_count") or 0)
        mode = str(sess.get("mode") or "burden")
        lines.append(f"  spar  {spars} ครั้ง · โหมด {mode}")
        loaned = list(sess.get("loaned") or [])
        if loaned:
            lines.append(f"  ยืม  {len(loaned)} ชิ้น")
        bb = worst_burden_band(player, reg)
        if bb == "crush":
            lines.append("  รู้สึก: หนักเกินตัว — โลกจริงควรพักขวัญ/ถอดเมื่อต่ำ")
            lines.append("  แนะนำ: ออกห้อง → ใส่ช่วงสั้น · Auto ถอดภาระเปิด (Policy B)")
        elif bb == "strain":
            lines.append("  รู้สึก: ร้อนมือ — ใช้ได้แต่ดูแลขวัญ")
            lines.append("  แนะนำ: ใช้ล่า/ดันสั้นได้ · พัก/กินเมื่อขวัญหด")
        elif sess.get("burden_muted") or mode == "power":
            lines.append("  รู้สึก: โหมดวัดพลัง — โทษปิด (สลับ b เพื่อรู้สึกภาระ)")
            lines.append("  แนะนำ: กด 3 → b แล้ว spar อีกครั้งเพื่อเทียบขวัญ")
        else:
            lines.append("  รู้สึก: ยังไม่กด (ลองยืม/ใส่เรลิกตำนาน+)")
            lines.append("  แนะนำ: เมนู 2 ยืม · 5 ใส่ · 4 spar · 7 สรุป")
        for bit in list(sess.get("log") or [])[-3:]:
            lines.append(f"  · {bit}")
    except Exception as exc:
        lines.append(f"  (สรุปข้าม: {exc})")
    lines.append("  (ห้อง · ไม่ได้เงินโลก · ออกแล้วของยืมคืน)")
    return lines


def spar_dummy(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: Optional[random.Random] = None,
    *,
    rounds: int = 2,
) -> List[str]:
    """
    WO-027: stronger multi-round sparring — no world money.
    Simulates pressure + burden ticks; never soft-deaths out of chamber floor.
    """
    if not in_godforge(player):
        return ["  ต้องอยู่ในห้องทดสอบก่อน"]
    rng = rng or random.Random(int(player.get("latent_seed") or 1))
    rounds = max(1, min(4, int(rounds or 2)))
    notes: List[str] = [f"── ซ้อม sparring ×{rounds} (ห้อง · แรงขึ้น) ──"]
    sess = _session(player)
    try:
        from game.domain.divine_burden import apply_burden_tick, soft_burden_status_line
        from game.domain.equipment import recompute_stats

        recompute_stats(player, reg)
        bl = soft_burden_status_line(player, reg)
        if bl:
            notes.append(f"  {bl}")
    except Exception:
        pass

    atk = int(player.get("power_atk") or player.get("atk") or 10)
    total_out = 0
    for r in range(1, rounds + 1):
        try:
            from game.domain.divine_burden import apply_burden_tick

            notes.extend(
                apply_burden_tick(player, reg, context="combat", rng=rng)
            )
        except Exception:
            pass
        # stronger dummy: more of player atk shown + dummy hits back harder
        # WO-030: clearer power feel — scales with atk + round heat
        heat = 1.0 + 0.12 * (r - 1)
        dmg = max(10, int(atk * (0.95 + rng.random() * 0.65) * heat))
        total_out += dmg
        notes.append(f"  รอบ {r}: ทุบหุ่น ~{dmg} (แรงจำลอง)")
        # WO-037/040: Anima presence + relic depth on first spar round
        if r == 1:
            try:
                from game.domain.stat_arch import anima_presence_lines

                notes.extend(
                    anima_presence_lines(player, "chamber_spar", reg=reg)
                )
            except Exception:
                pass
            try:
                from game.domain.relic_anima import on_chamber_spar_with_relic

                notes.extend(
                    on_chamber_spar_with_relic(player, reg, rounds=rounds)
                )
            except Exception:
                pass
        hp = int(player.get("hp") or 20)
        mhp = max(1, int(player.get("max_hp") or 20))
        chip = rng.randint(max(2, mhp // 22), max(4, mhp // 11))
        if r == rounds:
            chip = max(chip, mhp // 14)
        player["hp"] = max(mhp // 4, hp - chip)
        notes.append(f"    แรงสะท้อน · HP {player['hp']}/{mhp}")

    if sess.get("active"):
        sess["spar_count"] = int(sess.get("spar_count") or 0) + rounds
        log = list(sess.get("log") or [])
        log.append(f"spar×{rounds} แรงรวม~{total_out}")
        sess["log"] = log[-8:]
        player["godforge_session"] = sess

    notes.append(f"  รวมแรงประมาณ {total_out} · spar สะสม {sess.get('spar_count', rounds)}")
    notes.append("  (ห้อง · ไม่ได้เงินโลก)")
    # mini summary after spar
    notes.extend(format_chamber_burden_summary(player, reg)[1:4])
    return notes


def run_godforge_chamber(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
) -> None:
    """Interactive Godforge Chamber menu."""
    _inject_chamber_items(reg)
    while True:
        active = in_godforge(player)
        sess = _session(player) if active else {}
        mode = str(sess.get("mode") or "—")
        loaned = list(sess.get("loaned") or [])
        lines = [
            " ห้องทดสอบเรลิก · Godforge Chamber",
            "---",
            " ลองเรลิกอย่างปลอดภัย · ไม่ฟาร์มเงินโลก",
            f" สถานะ  {'อยู่ในห้อง' if active else 'นอกห้อง'}"
            + (f" · โหมด {mode}" if active else ""),
            f" ยืมแล้ว  {len(loaned)}/4",
        ]
        try:
            from game.domain.divine_burden import burden_summary_for_log

            lines.append(f" {burden_summary_for_log(player, reg)}")
        except Exception:
            pass
        lines.extend(
            [
                "---",
                " 1  เข้าห้อง" if not active else " 1  (อยู่ในห้องแล้ว)",
                " 2  ยืมเรลิกทดลอง",
                " 3  โหมด วัดภาระ / วัดพลัง",
                " 4  Sparring หุ่น (×2 รอบ · แรงขึ้น)",
                " 5  เปิดกระเป๋า/เกียร์ (ใส่ของยืม)",
                " 6  ออกห้อง (คืนของยืม + สรุป)",
                " 7  สรุปภาระตอนนี้ (God)",
                " 0  กลับ",
            ]
        )
        io.write_line()
        io.write_line(render_box(lines, double=False))
        ch = io.read_line("\n  Godforge> ").strip().lower()
        if ch in ("0", "", "q"):
            if active:
                conf = io.read_line("  ยังอยู่ในห้อง — ออกห้องก่อน? (y/N): ").strip().lower()
                if conf in ("y", "yes"):
                    for ln in exit_godforge(player, reg):
                        io.write_line(ln)
            return
        if ch == "1":
            for ln in enter_godforge(player, reg):
                io.write_line(ln)
        elif ch == "2":
            if not in_godforge(player):
                io.write_line("  เข้าห้องก่อน (1)")
                continue
            io.write_line("  เรลิกทดลอง:")
            for i, row in enumerate(CHAMBER_RELICS, 1):
                mark = "✓" if row["id"] in loaned else " "
                io.write_line(
                    f"   {i}. [{mark}] {row['name']} ({row.get('rarity')})"
                )
            pick = io.read_line("  เลือก 1–4: ").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(CHAMBER_RELICS):
                rid = CHAMBER_RELICS[int(pick) - 1]["id"]
                for ln in loan_relic(player, reg, rid):
                    io.write_line(ln)
        elif ch == "3":
            raw = io.read_line("  b=วัดภาระ / p=วัดพลัง: ").strip().lower()
            if raw in ("p", "power"):
                for ln in set_chamber_mode(player, "power"):
                    io.write_line(ln)
            else:
                for ln in set_chamber_mode(player, "burden"):
                    io.write_line(ln)
        elif ch == "4":
            raw = io.read_line("  จำนวนรอบ spar 1–3 [2]: ").strip()
            n = int(raw) if raw.isdigit() else 2
            for ln in spar_dummy(player, reg, random.Random(), rounds=n):
                io.write_line(ln)
        elif ch == "5":
            try:
                from game.services.field_menus import _manage_gear

                _manage_gear(player, reg, io)
            except Exception:
                io.write_line("  (เปิดเกียร์ไม่ได้ในโหมดนี้ — ใช้กระเป๋าหลัก)")
        elif ch == "6":
            for ln in exit_godforge(player, reg):
                io.write_line(ln)
        elif ch == "7":
            if not in_godforge(player):
                io.write_line("  เข้าห้องก่อน (1)")
                continue
            for ln in format_chamber_burden_summary(player, reg):
                io.write_line(ln)
            io.read_line("Enter...")

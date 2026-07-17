"""
WO-Storage-1 — PERSONAL warehouse hub (คลังส่วนตัว).

Entry: PERSONAL → 7 / U
Login: pass each open (session unlock until PERSONAL exit)
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from game.data_load.registry import DataRegistry
from game.domain.warehouse import (
    MONEY_KEYS,
    MONEY_LABEL,
    auto_stash_enabled,
    bag_mat_junk_indices,
    default_user,
    deposit_items_batch,
    deposit_money,
    format_bag_deposit_lines,
    format_warehouse_item_lines,
    format_warehouse_status_lines,
    is_setup,
    is_unlocked,
    login,
    lock_session,
    money_held,
    money_stored,
    parse_slot_spec,
    parse_withdraw_spec,
    register,
    require_unlocked,
    set_auto_stash,
    slots_cap,
    slots_used,
    withdraw_items_batch,
    withdraw_money,
)
from game.ports.io import IO
from game.ui_terminal.layout import render_box


def _read_secret(io: IO, prompt: str) -> str:
    """
    Prefer getpass when TTY; ScriptedIO / non-TTY falls back to read_line.
    """
    try:
        import getpass
        import sys

        # ScriptedIO has no real stdin secret — use read_line path
        if type(io).__name__ == "ScriptedIO":
            return io.read_line(prompt).strip()
        if hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            # still show prompt via io for capture consistency
            io.write(prompt)
            return getpass.getpass("").strip()
    except Exception:
        pass
    return io.read_line(prompt).strip()


def _ensure_access(player: Dict[str, Any], io: IO) -> bool:
    """
    Shared team vault: any character with correct user+pass opens the same vault.
    - Vault exists → login
    - Not found → create (register) with confirm pass
    """
    if is_unlocked(player) and is_setup(player):
        return True

    from game.domain.warehouse import ensure_warehouse, vault_exists, _world_id

    ensure_warehouse(player)
    hint = default_user(player)
    lines = [
        " คลังทีม · แชร์ user + pass",
        "---",
        " ใครรู้รหัส (โลกเดียวกัน) ใช้คลังร่วมกันได้",
        " เก็บได้: เกียร์ · ยา · อาหาร · mat · เงิน",
        f" ชื่อคลัง (Enter=「{hint}」)",
        "---",
        " 0  ยกเลิก",
    ]
    io.write_line()
    io.write_line(render_box(lines, double=False))
    user_in = io.read_line("  ชื่อคลัง (user): ").strip()
    if user_in in ("0", "q", "Q"):
        return False
    uname = user_in or hint
    wid = _world_id(player)
    exists = vault_exists(wid, uname)

    if exists:
        pw = _read_secret(io, "  รหัสผ่าน: ")
        if pw in ("0", "q", "Q", ""):
            return False
        ok, msg = login(player, pw, user=uname)
        io.write_line()
        io.write_line(render_box([" คลังทีม", "---", f"  {msg}"], double=False))
        return ok

    # create new shared vault
    io.write_line(f"  ยังไม่มีคลัง 「{uname}」 — สร้างใหม่")
    pw = _read_secret(io, "  ตั้งรหัสผ่าน: ")
    if not pw or pw in ("0",):
        io.write_line("  ยกเลิกสร้างคลัง")
        return False
    pw2 = _read_secret(io, "  ยืนยันรหัสผ่าน: ")
    if pw != pw2:
        io.write_line(
            render_box([" คลังทีม", "---", "  รหัสผ่านไม่ตรงกัน"], double=False)
        )
        return False
    ok, msg = register(player, pw, user=uname)
    io.write_line()
    io.write_line(render_box([" คลังทีม", "---", f"  {msg}"], double=False))
    return ok


def run_warehouse_hub(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
) -> None:
    """Main warehouse loop until 0 (keeps session unlock for PERSONAL)."""
    if not _ensure_access(player, io):
        return

    while True:
        ok, msg = require_unlocked(player)
        if not ok:
            io.write_line(f"  {msg}")
            if not _ensure_access(player, io):
                return

        io.write_line()
        io.write_line(render_box(format_warehouse_status_lines(player), double=False))
        menu = [
            " เมนูคลังทีม",
            "---",
            "  1  ดูของในคลัง",
            "  2  ฝากของจากกระเป๋า  (เกียร์/ยา/mat ได้)",
            "  3  ถอนของเข้ากระเป๋า",
            "  4  ฝากเงิน",
            "  5  ถอนเงิน",
            f"  6  Auto stash  (ตอนนี้: {'เปิด' if auto_stash_enabled(player) else 'ปิด'})",
            "---",
            "  0  กลับ (ล็อกคลังเมื่อออกตัวละคร)",
        ]
        try:
            from game.config import APP_VERSION

            menu.append(f"         build {str(APP_VERSION).replace('-alpha', '')}")
        except Exception:
            pass
        io.write_line()
        io.write_line(render_box(menu, double=False))
        ch = io.read_line("\n  〔คลัง〕 เลือก: ").strip().lower()

        if ch in ("0", "q", ""):
            break
        if ch == "1":
            io.write_line()
            io.write_line(
                render_box(format_warehouse_item_lines(player, reg), double=False)
            )
            io.read_line("  Enter...")
        elif ch == "2":
            _deposit_item_flow(player, reg, io)
        elif ch == "3":
            _withdraw_item_flow(player, reg, io)
        elif ch == "4":
            _money_flow(player, io, deposit=True)
        elif ch == "5":
            _money_flow(player, io, deposit=False)
        elif ch == "6":
            cur = auto_stash_enabled(player)
            msg2 = set_auto_stash(player, not cur)
            io.write_line()
            io.write_line(
                render_box(
                    [
                        " Auto stash",
                        "---",
                        f"  {msg2}",
                        "  ย้าย mat/junk/ยา/อาหาร เมื่อกระเป๋าใกล้เต็ม",
                        "  (ไม่แตะเกียร์/เรลิก/การ์ด · ต้องเข้าคลัง session นี้)",
                    ],
                    double=False,
                )
            )
            io.read_line("  Enter...")
        else:
            io.write_line("  1–6 · 0 กลับ")


def _batch_result_box(
    title: str,
    ok_lines: list,
    skip: list,
    footer: str,
) -> list:
    lines = [f" {title}", "---"]
    if ok_lines:
        lines.append(f" สำเร็จ  {len(ok_lines)} ช่อง")
        for s in ok_lines[:12]:
            lines.append(f"  · {s}")
        if len(ok_lines) > 12:
            lines.append(f"  · …และอีก {len(ok_lines) - 12}")
    else:
        lines.append(" สำเร็จ  0 ช่อง")
    if skip:
        lines.append("---")
        lines.append(f" ข้าม  {len(skip)}")
        for s in skip[:5]:
            lines.append(f"  · {s}")
    lines.append("---")
    lines.append(f" {footer}")
    return lines


def _deposit_item_flow(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    """WO-Storage-1.1: multi / range / a=mat+junk only."""
    io.write_line()
    io.write_line(render_box(format_bag_deposit_lines(player, reg), double=False))
    n_mat = len(bag_mat_junk_indices(player, reg))
    io.write_line(
        f"  ใบ้: หลายช่อง · ช่วง · a=mat/junk/ยา/อาหาร ({n_mat}) · เกียร์เลือกเลข"
    )
    raw = io.read_line(
        "  เลขช่องฝาก (0=ยกเลิก · a=bulk soft): "
    ).strip()
    if raw in ("0", "", "q"):
        return
    ids = list(player.get("inventory_ids") or [])
    nmax = len(ids)
    if nmax <= 0:
        io.write_line("  กระเป๋าว่าง")
        return
    idxs, err = parse_slot_spec(raw, max_index_1based=nmax)
    if err == "cancel":
        return
    if err == "auto_mat":
        idxs = bag_mat_junk_indices(player, reg)
        if not idxs:
            io.write_line()
            io.write_line(
                render_box(
                    [
                        " ฝากของ",
                        "---",
                        "  ไม่มี mat/junk/ยา/อาหาร ในกระเป๋า",
                        "  (a ไม่ย้ายเกียร์/เรลิก — ฝากเกียร์ด้วยเลขช่อง)",
                    ],
                    double=False,
                )
            )
            io.read_line("  Enter...")
            return
    elif err:
        io.write_line(f"  {err}")
        return
    if not idxs:
        io.write_line("  ไม่ได้เลือกช่อง")
        return

    ok_lines, skip = deposit_items_batch(player, reg, idxs, full_stack=True)
    footer = f" คลัง  {slots_used(player)}/{slots_cap(player)}"
    io.write_line()
    io.write_line(
        render_box(_batch_result_box("ฝากของ", ok_lines, skip, footer), double=False)
    )
    io.read_line("  Enter...")


def _withdraw_item_flow(player: Dict[str, Any], reg: DataRegistry, io: IO) -> None:
    """WO-Storage-1.1: multi / n:qty / range full stacks."""
    from game.domain.warehouse import ensure_warehouse
    from game.runtime.inventory_auto import bag_used
    from game.domain.inventory_sys import BAG_SOFT_CAP

    io.write_line()
    io.write_line(render_box(format_warehouse_item_lines(player, reg), double=False))
    io.write_line("  ใบ้: 1:4 = ช่อง1 ถอน4 · หลายช่อง 1:3 2:1 · ช่วง 2-3 ทั้งสแตก")
    raw = io.read_line("  เลขช่องถอน (0=ยกเลิก): ").strip()
    if raw in ("0", "", "q"):
        return
    ensure_warehouse(player)
    ids = list((player["warehouse"]["items"] or {}).get("inventory_ids") or [])
    nmax = len(ids)
    if nmax <= 0:
        io.write_line("  คลังว่าง")
        return
    picks, err = parse_withdraw_spec(raw, max_index_1based=nmax)
    if err == "cancel":
        return
    if err:
        io.write_line(f"  {err}")
        return
    if not picks:
        io.write_line("  ไม่ได้เลือกช่อง")
        return

    ok_lines, skip = withdraw_items_batch(player, reg, picks)
    bag_cap = int(player.get("bag_cap") or BAG_SOFT_CAP or 40)
    footer = f" กระเป๋า  {bag_used(player)}/{bag_cap}"
    io.write_line()
    io.write_line(
        render_box(_batch_result_box("ถอนของ", ok_lines, skip, footer), double=False)
    )
    io.read_line("  Enter...")


def _money_flow(player: Dict[str, Any], io: IO, *, deposit: bool) -> None:
    """Enter amount blank = all of that currency."""
    title = "ฝากเงิน" if deposit else "ถอนเงิน"
    lines = [
        f" {title}",
        "---",
        "  1  โลก",
        "  2  สวรรค์",
        "  3  นรก",
        "  0  ยกเลิก",
        "---",
        "  จำนวน: ใส่ตัวเลข · Enter = ทั้งหมด",
    ]
    io.write_line()
    io.write_line(render_box(lines, double=False))
    ch = io.read_line("  สกุล: ").strip()
    key_map = {
        "1": "world",
        "2": "heaven",
        "3": "hell",
        "w": "world",
        "h": "heaven",
        "n": "hell",
    }
    if ch in ("0", "q", ""):
        return
    key = key_map.get(ch.lower())
    if not key:
        cl = ch.lower()
        if cl in MONEY_KEYS:
            key = cl
        elif "โลก" in ch:
            key = "world"
        elif "สวรรค์" in ch:
            key = "heaven"
        elif "นรก" in ch:
            key = "hell"
        else:
            io.write_line("  เลือก 1–3")
            return
    avail = money_held(player, key) if deposit else money_stored(player, key)
    raw = io.read_line(
        f"  จำนวน{MONEY_LABEL[key]} (Enter=ทั้งหมด {avail}): "
    ).strip()
    if not raw:
        amount = avail
    else:
        try:
            amount = int(raw)
        except Exception:
            io.write_line("  จำนวนไม่ถูกต้อง")
            return
    if amount <= 0:
        io.write_line("  ไม่มีเงินให้ทำรายการ")
        return
    if deposit:
        ok, msg = deposit_money(player, key, amount)
    else:
        ok, msg = withdraw_money(player, key, amount)
    io.write_line()
    io.write_line(render_box([f" {title}", "---", f"  {msg}"], double=False))
    io.read_line("  Enter...")


def lock_warehouse_on_personal_exit(player: Dict[str, Any]) -> None:
    """Call when leaving PERSONAL hub."""
    lock_session(player)

"""
WO-Arena-1 — Interactive Arena entry (city / special).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from game.data_load.registry import DataRegistry
from game.domain.arena import (
    TIER_LABEL_TH,
    available_companions,
    ensure_arena_state,
    format_session_summary,
    reveal_invite_soft,
    roll_mystery_invite,
    run_arena_session_logic,
    select_lineup,
)
from game.ports.io import IO
from game.ui_terminal.layout import render_box


def _can_enter_arena(player: Dict[str, Any]) -> tuple:
    loc = str(player.get("location") or "")
    if loc in ("ancient_city", "crystal_peak"):
        return True, ""
    # allow if player has flag or deepest unlocked
    st = ensure_arena_state(player)
    if st.get("unlocked_tiers") and len(st.get("unlocked_tiers") or []) > 1:
        return True, ""
    return False, "อารีน่าอยู่ที่เมืองโบราณ (หรือยอดผลึก) — เดินทางไปก่อน"


def run_arena_menu(
    player: Dict[str, Any],
    reg: DataRegistry,
    io: IO,
    rng: Optional[random.Random] = None,
) -> None:
    """Main arena hub — mystery invite · lineup · 3-round session."""
    rng = rng or random.Random(int(player.get("latent_seed") or 1) + int(player.get("time_units") or 0))
    ok, why = _can_enter_arena(player)
    if not ok:
        io.write_line(f"  {why}")
        return

    st = ensure_arena_state(player)
    while True:
        deepest = TIER_LABEL_TH.get(str(st.get("deepest_tier") or "normal"), "สามัญ")
        unlocked = [
            TIER_LABEL_TH.get(t, t) for t in (st.get("unlocked_tiers") or ["normal"])
        ]
        lines = [
            " ลานอารีน่า · สนามเงา",
            "---",
            " ทีม 1–4 (คุณ + ซุ่มสูงสุด 3) · 3 รอบ · คะแนนกลยุทธ์",
            " แพ้รอบยังได้คะแนน · คะแนนรวมสูงไขชั้นลึกได้",
            "---",
            f" ชั้นลึกสุดที่เคยไข 〔{deepest}〕",
            f" ปลดแล้ว: {', '.join(unlocked)}",
            f" ครั้งที่ลง {int(st.get('sessions') or 0)} · แต้มดีสุด ~{int(st.get('best_total') or 0)}",
            "---",
            "  1  รับใบเชิญ Mystery · ลงสนาม",
            "  2  ดูทีมปัจจุบัน / ซุ่ม",
            "  0  ออกจากลาน",
        ]
        io.write_line()
        io.write_line(render_box(lines, double=False))
        ch = io.read_line("\n  เลือก: ").strip().lower()
        if ch in ("0", "", "q"):
            return
        if ch == "2":
            comps = available_companions(player)
            io.write_line(f"  ซุ่มในปาร์ตี้ {len(comps)}/3")
            for i, m in enumerate(comps, 1):
                io.write_line(f"   {i}. {m.get('name') or m.get('id')}")
            if not comps:
                io.write_line("  (ยังไม่มีซุ่ม — เข้าคนเดียวได้)")
            continue
        if ch != "1":
            io.write_line("  พิมพ์ 1 / 2 / 0")
            continue

        # Mystery invite
        invite = roll_mystery_invite(player, reg, rng)
        io.write_line()
        io.write_line(
            render_box(
                [
                    " ใบเชิญ Mystery",
                    "---",
                    f" {invite.get('label')} — {invite.get('soft_pressure')}",
                    " ไม่รู้หน้าตา/สถิติ · อาศัยประสบการณ์",
                    "---",
                    "  1  รับเชิญ · เลือกทีม",
                    "  0  ปฏิเสธ",
                ],
                double=False,
            )
        )
        acc = io.read_line("\n  รับเชิญ? ").strip().lower()
        if acc not in ("1", "y", "yes", "ใช่"):
            io.write_line("  เงาใบเชิญจางหาย")
            continue

        io.write_line(f"  {reveal_invite_soft(invite)}")

        # Lineup
        comps = available_companions(player)
        lineup_ids: List[str] = []
        if comps:
            io.write_line()
            io.write_line(" เลือกซุ่มขึ้นสนาม (เว้นว่าง = คนเดียว · เลขคั่น comma เช่น 1,2)")
            for i, m in enumerate(comps, 1):
                io.write_line(f"   {i}. {m.get('name') or m.get('id')}")
            raw = io.read_line("  ซุ่ม: ").strip()
            if raw:
                try:
                    idxs = [int(x.strip()) for x in raw.replace(" ", "").split(",") if x.strip()]
                    lineup_ids = select_lineup(player, idxs)
                except Exception:
                    io.write_line("  รูปแบบไม่ถูก — เข้าคนเดียว")
                    lineup_ids = []
        team_n = 1 + len(lineup_ids)
        io.write_line(f"  ทีม {team_n} คน · เริ่ม 3 รอบ…")
        if team_n == 1:
            io.write_line("  (คนเดียว — คะแนน Team ต่ำ · ชั้นสูงยาก)")

        # Run session (simulated combat + score)
        result = run_arena_session_logic(
            player,
            reg,
            rng,
            tier=str(invite.get("tier") or "normal"),
            lineup_ids=lineup_ids,
        )
        io.write_line()
        io.write_line(render_box(format_session_summary(result), double=False))
        st = ensure_arena_state(player)
        io.read_line("\n  Enter กลับลาน…")

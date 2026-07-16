#!/usr/bin/env python3
"""WO-053 Personal System harness — temple → growth → panel."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.config import APP_VERSION, DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.auto_growth import activate_auto_growth_if_needed, pulse_auto_growth
from game.domain.character import create_player
from game.domain.personal_system import (
    format_personal_narrative_panel,
    journal_lines,
    maybe_seed_opening_journal,
    note_anima_story,
    note_bond_story,
)
from game.domain.progression import ensure_progression
from game.domain.stat_grades import temple_unlock
from game.domain.world_relations import adjust_faction


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, scores = [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    p = create_player(reg, "wo053", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["level"] = 12
    p["stat_points"] = 8
    p["mana"] = 50
    maybe_seed_opening_journal(p)
    scores["prologue"] = 5 if (p.get("personal_journal") or []) else 2
    log("prologue", journal_lines(p, limit=2)[0] if journal_lines(p) else "empty")

    # temple
    temple_unlock(p, reg)
    j = "\n".join(journal_lines(p, limit=8))
    scores["temple"] = 5 if ("วิหาร" in j or "ปลด" in j) and p.get("grade_revealed") else 2
    log("temple", j.replace("\n", " | ")[:140])

    # panel sections
    panel = "\n".join(format_personal_narrative_panel(p, reg))
    need = ("เรื่องของฉัน", "เกรด", "อ่านชั้น", "จิต", "เรลิก", "สายตา", "เติบโต", "บันทึก")
    scores["panel"] = 5 if all(any(k in panel for k in (s,)) for s in need[:1]) and "เกรด" in panel and "บันทึก" in panel else 2
    # stricter
    ok_sec = sum(
        1
        for s in ("เกรด", "อ่านชั้น", "เรลิก", "สายตา", "เติบโต", "บันทึก")
        if s in panel
    )
    scores["panel"] = 5 if ok_sec >= 5 and "power_" not in panel.lower() else 2
    log("panel", f"sections={ok_sec} len={len(panel)}")

    # faction + anima + bond journal
    adjust_faction(p, "divine", 10, force_alert=True)
    note_anima_story(p, "relic_equip")
    note_bond_story(p, "resonance", "divine")
    j2 = "\n".join(journal_lines(p, limit=12))
    scores["stories"] = 5 if ("เทพ" in j2 or "Anima" in j2 or "เรโซแนนซ์" in j2 or "เรลิก" in j2) else 2
    log("stories", j2.replace("\n", " | ")[:160])

    # lv30 growth arc
    p["level"] = 30
    p["stat_points"] = 3
    activate_auto_growth_if_needed(p, reg)
    for _ in range(4):
        pulse_auto_growth(p, "quest", reg=reg)
    panel30 = "\n".join(format_personal_narrative_panel(p, reg))
    scores["growth"] = 5 if ("ไหล" in panel30 or "เติบโต" in panel30) else 2
    log("growth", panel30[panel30.find("⑥") : panel30.find("⑥") + 120] if "⑥" in panel30 else "ok")

    # no leak
    leak = any(x in (panel + panel30).lower() for x in ("power_atk", "1.40", "axis_progress"))
    scores["soft"] = 5 if not leak else 1
    log("soft", "ok" if not leak else "LEAK")

    # journal ring
    scores["journal"] = 5 if len(p.get("personal_journal") or []) >= 2 else 2
    log("journal", f"n={len(p.get('personal_journal') or [])}")

    avg = sum(scores.values()) / len(scores)
    all_pass = all(v >= 3 for v in scores.values())
    out = ROOT / "exports"
    out.mkdir(exist_ok=True)
    payload = {
        "version": APP_VERSION,
        "scores": scores,
        "notes": notes,
        "all_pass": all_pass,
        "avg": avg,
    }
    (out / "wo053_personal_system.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-053 Personal System · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-054\n\n")
    md.append("**แข็ง:** เรื่องของฉัน รวมเกรด/Anima/เรลิก/faction/โต · journal soft\n\n")
    md.append("**อ่อน:** content journal ยังบาง · weakness combat ยังไม่ผูก\n\n")
    md.append("**WO-054:** Soft Combat Identity / weakness lite หรือ content Moments\n")
    (out / "WO053_PERSONAL_SYSTEM.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-053 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

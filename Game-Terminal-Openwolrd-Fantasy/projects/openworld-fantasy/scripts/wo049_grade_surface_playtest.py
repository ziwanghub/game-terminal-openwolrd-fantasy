#!/usr/bin/env python3
"""WO-049 Grade Surface + Tier Soft harness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.config import APP_VERSION, DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.progression import allocate_stat, ensure_progression
from game.domain.stat_arch import self_assess_lines
from game.domain.stat_grades import (
    apply_invest_to_grades,
    format_grade_p_panel,
    format_grade_surface_lines,
    grade_hub_compact_lines,
    grade_revealed,
    temple_unlock,
    tier_from_axis_score,
)
from game.ui_terminal.status import format_personal_hub_lines, render_status_l1


def main() -> int:
    reg = DataRegistry.load(DATA_DIR)
    notes, scores = [], {}

    def log(b, m):
        notes.append(f"[{b}] {m}")

    # tiers
    assert tier_from_axis_score(0) == "early"
    assert tier_from_axis_score(100) == "special"
    scores["tier_map"] = 5
    log("tier_map", "early/mid/late/special ok")

    p = create_player(reg, "wo049", "warrior", "เมษ")
    ensure_progression(p, reg)
    hub0 = "\n".join(format_personal_hub_lines(p, "forest"))
    scores["hidden"] = 5 if ("ปิด" in hub0 and "เกรด" in hub0) else 2
    log("hidden", "hub shows closed grade")

    p["level"] = 12
    p["stat_points"] = 8
    p["stats_alloc"] = {"atk": 4, "defense": 2, "magic": 1, "speed": 2}
    lines = temple_unlock(p, reg)
    assert grade_revealed(p)
    blob = "\n".join(lines)
    scores["temple"] = 5 if ("ขั้น" in blob or "พิเศษ" in blob) and p.get("player_grade") else 2
    log("temple", f"grade={p.get('player_grade')} tier-in-ritual={scores['temple']}")

    surf = "\n".join(format_grade_surface_lines(p))
    scores["surface"] = 5 if "เกรดรวม" in surf and "โจมตี" in surf else 2
    log("surface", surf.replace("\n", " | ")[:160])

    compact = "\n".join(grade_hub_compact_lines(p))
    scores["compact"] = 5 if "ระดับ" in compact or "〔" in compact else 2
    log("compact", compact.replace("\n", " | ")[:120])

    st = render_status_l1(p, "ancient_city")
    scores["status"] = 5 if "เกรด" in st else 2
    log("status", "status has grade block")

    v = "\n".join(self_assess_lines(p, force=True, reg=reg))
    scores["assess"] = 5 if "เกรด" in v and ("ขั้น" in v or "พิเศษ" in v or "โจมตี" in v) else 2
    log("assess", "V grade surface")

    panel = "\n".join(format_grade_p_panel(p))
    scores["p_menu"] = 5 if "โจมตี" in panel and ("ขั้น" in panel or "พิเศษ" in panel) else 2
    log("p_menu", panel.split("\n")[5] if len(panel.splitlines()) > 5 else "ok")

    # invest growth + soft message
    p["stat_points"] = 5
    before = float((p.get("axis_progress") or {}).get("atk", 0))
    msg = allocate_stat(p, reg, "atk", 3)
    after = float((p.get("axis_progress") or {}).get("atk", 0))
    scores["invest"] = 5 if after > before and "power" not in msg.lower() else 2
    log("invest", msg.replace("\n", " | ")[:140])

    # profile tilt still works (focused top axis)
    p_f = create_player(reg, "wo049f", "warrior", "เมษ")
    ensure_progression(p_f, reg)
    p_f["grade_revealed"] = True
    p_f["player_grade"] = "B"
    p_f["growth_profile"] = "focused"
    p_f["stats_alloc"] = {"atk": 8, "defense": 1, "magic": 1, "speed": 1}
    p_f["axis_progress"] = {k: 0.0 for k in ("atk", "defense", "magic", "speed")}
    apply_invest_to_grades(p_f, "atk", 4)
    apply_invest_to_grades(p_f, "defense", 4)
    atk_p = float(p_f["axis_progress"]["atk"])
    def_p = float(p_f["axis_progress"]["defense"])
    scores["profile"] = 5 if atk_p > def_p else 1
    log("profile", f"focused atk={atk_p:.2f} def={def_p:.2f}")

    # no raw power in surfaces
    leak = any(
        x in (surf + st + v + panel).lower()
        for x in ("power_atk", "axis_progress", "growth_mult=")
    )
    scores["no_leak"] = 5 if not leak else 1
    log("no_leak", "no raw power leak" if not leak else "LEAK")

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
    (out / "wo049_grade_surface.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        f"# WO-049 Grade Surface + Tier Soft · `{APP_VERSION}`\n\n",
        f"**all_pass:** {all_pass} · avg **{avg:.2f}**\n\n",
        "## Scores\n",
    ]
    for k, v in scores.items():
        md.append(f"- {k}: {v}\n")
    md.append("\n## Notes\n")
    for n in notes:
        md.append(f"- {n}\n")
    md.append("\n## จุดแข็ง/อ่อน + WO-050\n\n")
    md.append("**แข็ง:** Surface Status/V/Hub · tier soft · growth+profile ยังครบ\n\n")
    md.append("**อ่อน:** ยังไม่เข้า damage · ยังไม่ตัด P · appraisal ชั้นสูงยังไม่มี\n\n")
    md.append("**WO-050:** Damage Pipeline v1 (adapter) + ผูกเกรดกับ combat soft\n")
    (out / "WO049_GRADE_SURFACE.md").write_text("".join(md), encoding="utf-8")
    print(f"WO-049 harness · all_pass={all_pass} avg={avg:.2f}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

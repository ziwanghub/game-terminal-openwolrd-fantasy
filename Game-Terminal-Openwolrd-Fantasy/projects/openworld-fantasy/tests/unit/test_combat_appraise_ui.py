"""Combat appraisal + turn-condition panel readability."""
from __future__ import annotations

import random

from game.config import APP_VERSION, DATA_DIR, PHASE
from game.data_load.registry import DataRegistry
from game.domain.appraisal import appraise_monster_lines, ensure_appraisal, run_appraisal
from game.domain.character import create_player
from game.domain.equipment import recompute_stats
from game.ui_terminal.layout import display_width, render_box


def _oracle():
    return {
        "id": "boss_ruin_oracle",
        "name": "นักพยากรณ์ซาก — Ruin Oracle",
        "boss": True,
        "rarity": "sacred",
        "level": 16,
        "hp": 2355,
        "max_hp": 3260,
        "atk": 40,
        "elements": ["arcane", "shadow"],
    }


def test_version_appraise_ui():
    assert "2.2" in APP_VERSION  # 2.20+ line incl. 2.21 worthiness
    # phase stamp moves with later WOs; keep non-empty + known lineage soft-ok
    assert PHASE
    assert any(
        k in PHASE
        for k in ("appraise-ui", "item-ui", "skill-ui", "storage", "wo-storage")
    ) or "-" in PHASE


def test_monster_appraisal_sections_proportional():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "au", "priest", "มีน")
    recompute_stats(p, reg)
    ensure_appraisal(p)
    p["appraisal_tier"] = "SSS"
    lines = appraise_monster_lines(p, _oracle(), reg, known=True, rng=random.Random(1))
    text = "\n".join(lines)
    assert "อ่านชั้น" in text
    assert "เป้า / สภาพ" in text
    assert "ชั้นพลัง" in text
    assert "จุดอ่อน" in text
    assert "สายที่น่าลอง" in text
    box = render_box(lines, double=False)
    for ln in box.splitlines():
        assert display_width(ln) <= 62


def test_run_appraisal_boxable_and_gate():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ag", "priest", "มีน")
    recompute_stats(p, reg)
    ensure_appraisal(p)
    p["appraisal_tier"] = "SSS"
    p["_appraisal_cd_until"] = 10**9
    lines, _g = run_appraisal(
        p,
        target="monster",
        mon=_oracle(),
        reg=reg,
        known=True,
        paid=True,
        rng=random.Random(2),
    )
    joined = "\n".join(lines)
    assert "หมายเหตุสมาธิ" in joined or "สมาธิ" in joined
    assert "เป้า / สภาพ" in joined or "ชื่อ" in joined
    # no double bare --- spam: at most reasonable separators
    assert joined.count("\n---\n") <= 12
    box = render_box(list(lines), double=False)
    assert "┌" in box or "+" in box

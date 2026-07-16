"""WO-036 polish: assess UX, enemy assess, luck caps."""
from __future__ import annotations

from game.config import DATA_DIR
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.inventory_sys import upgrade_success_chance
from game.domain.party import assist_chance_for_member
from game.domain.progression import allocate_stat, ensure_progression
from game.domain.stat_arch import enemy_assess_lines, self_assess_lines, ensure_stat_arch


def test_self_assess_sections_clear():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w36a", "warrior", "เมษ")
    ensure_progression(p, reg)
    lines = self_assess_lines(p, force=True, reg=reg)
    blob = "\n".join(lines)
    assert "①" in blob or "ชีพ" in blob
    assert "ขวัญ" in blob
    assert "จิตวิญญาณ" in blob
    assert "คนละชั้น" in blob or "กำลังใจ" in blob
    assert p.get("_self_assess_done") is True


def test_enemy_assess_soft_no_raw_stats():
    mon = {
        "name": "หมาป่า",
        "level": 5,
        "hp": 20,
        "max_hp": 40,
        "atk": 12,
    }
    p = {"level": 4, "anima": 50.0}
    lines = enemy_assess_lines(mon, p, known=True)
    blob = "\n".join(lines)
    assert "ประเมินศัตรู" in blob
    assert "atk" not in blob.lower() or "คม" in blob
    assert "12" not in blob  # no raw atk dump
    assert "40" not in blob  # no raw max hp


def test_allocate_soft_message_points_to_v():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "w36b", "warrior", "เมษ")
    ensure_progression(p, reg)
    p["stat_points"] = 2
    msg = allocate_stat(p, reg, "atk", 1)
    # soft feel (grade may still be locked → V/วิหาร path)
    assert any(
        k in msg
        for k in ("หนา", "〔", "มือ", "หนัก", "รู้สึก", "โจมตี")
    )
    assert "V" in msg or "ประเมิน" in msg or "วิหาร" in msg


def test_luck_upgrade_bias_capped():
    reg = DataRegistry.load(DATA_DIR)
    hi = upgrade_success_chance(
        "main_hand", 3, reg=reg, rarity_id="rare", player={"luck_score": 0.45}
    )
    lo = upgrade_success_chance(
        "main_hand", 3, reg=reg, rarity_id="rare", player={"luck_score": -0.25}
    )
    assert hi >= lo
    assert (hi - lo) <= 0.15


def test_assist_luck_bias_capped():
    p = {"luck_score": 0.45, "party_bonds": {"c1": 50}}
    lucky = assist_chance_for_member(p, "c1")
    p["luck_score"] = -0.25
    unlucky = assist_chance_for_member(p, "c1")
    assert abs(lucky - unlucky) <= 0.12

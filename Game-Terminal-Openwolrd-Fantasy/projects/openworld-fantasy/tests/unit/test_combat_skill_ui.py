"""Combat skill picker / combo result boxes — readable layout."""
from __future__ import annotations

from game.config import APP_VERSION, DATA_DIR, PHASE
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.combat import skill_options
from game.domain.equipment import recompute_stats
from game.ui_terminal.combat_skills import (
    format_combo_open_lines,
    format_combo_result_lines,
    format_skill_menu_lines,
    render_combo_open_box,
    render_combo_result_box,
    render_skill_menu_box,
    _wrap_arrow_chain,
)
from game.ui_terminal.layout import display_width


def test_version_skill_ui():
    assert "2.20" in APP_VERSION
    assert PHASE
    assert any(
        k in PHASE
        for k in ("skill-ui", "item-ui", "appraise-ui", "item-free", "storage", "wo-storage")
    ) or "-" in PHASE


def test_skill_menu_box_has_columns_and_help():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "sui", "mage", "เมถุน")
    recompute_stats(p, reg)
    opts = skill_options(p, reg)
    assert opts
    text = render_skill_menu_box(opts, p, reg, max_combo=5)
    assert "สกิล" in text or "คอมโบ" in text
    assert "MP" in text
    assert "ตัวอย่าง" in text
    assert "┌" in text or "+" in text
    # proportional width
    for line in text.splitlines():
        assert display_width(line) <= 62


def test_chain_wrap_breaks_between_skills():
    names = [
        "กระสุนน้ำ",
        "ลมบาด",
        "ประกายสายฟ้า",
        "【Unit】ฝุ่นในกระเป๋า",
        "อ่านชั้น",
    ]
    lines = _wrap_arrow_chain(names, inner=40)
    assert len(lines) >= 2
    joined = " ".join(lines)
    assert "กระสุนน้ำ" in joined
    assert "อ่านชั้น" in joined
    assert "→" in joined


def test_combo_open_and_result_boxes():
    open_lines = format_combo_open_lines(
        length=3,
        chain_names=["กระสุนน้ำ", "ลมบาด", "ประกายสายฟ้า"],
        flavor="ฝีเท้า-มานา-เจตนาประสาน: พายุน้ำแข็งสายฟ้า!",
        mind_notes=["เรียงท่ามากไป — จิตกระจัดชั่วคราว"],
    )
    assert any("คอมโบ" in x for x in open_lines)
    assert any("โซ่" in x for x in open_lines)
    assert any("หลอม" in x for x in open_lines)

    res = format_combo_result_lines(
        damage=385,
        mana_cost=42,
        length=3,
        flavor_tag="(ได้ผลดี!)",
        enemy_soft="ยังไหว",
        resist_line="ความหนาวยังไม่เกาะ",
        fight_log_line="T3 ▸ คุณ 「คอมโบ×3」 → ??? 〔เวท〕385",
    )
    text = "\n".join(res)
    assert "385" in text
    assert "−42" in text or "-42" in text
    assert "3 ขั้น" in text

    box = render_combo_result_box(
        damage=385, mana_cost=42, length=3, flavor_tag="·มืด"
    )
    assert "ผล" in box
    assert "ดาเมจ" in box


def test_single_skill_open_title():
    lines = format_combo_open_lines(
        length=1, chain_names=["ลูกไฟ"], flavor=""
    )
    assert any("ลงมือ" in x for x in lines)
    assert any("ลูกไฟ" in x for x in lines)

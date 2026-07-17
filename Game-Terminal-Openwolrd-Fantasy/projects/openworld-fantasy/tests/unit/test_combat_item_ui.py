"""Combat item care UI — proportional consumable list / result boxes."""
from __future__ import annotations

from game.config import APP_VERSION, DATA_DIR, PHASE
from game.data_load.registry import DataRegistry
from game.domain.character import create_player
from game.domain.equipment import add_item, recompute_stats
from game.domain.needs import ensure_needs
from game.services.consumables import _use_potion
from game.ui_terminal.combat_skills import (
    consumable_effect_hint,
    consumable_kind_tag,
    format_consumable_menu_lines,
    render_consumable_menu_box,
    render_item_care_hub_box,
    render_item_use_result_box,
)
from game.ui_terminal.layout import display_width


class _IO:
    def __init__(self, answers=None):
        self.answers = list(answers or [])
        self.lines: list[str] = []

    def write_line(self, text: str = "") -> None:
        self.lines.append(str(text))

    def read_line(self, prompt: str = "") -> str:
        if self.answers:
            return self.answers.pop(0)
        return "0"

    def joined(self) -> str:
        return "\n".join(self.lines)


def test_version_item_ui():
    assert "2.20" in APP_VERSION
    assert PHASE
    assert any(
        k in PHASE for k in ("item-ui", "skill-ui", "item-free", "storage", "wo-storage")
    ) or "-" in PHASE


def test_effect_hints():
    assert "HP+" in consumable_effect_hint({"heal_hp": 55})
    assert "MP+" in consumable_effect_hint({"heal_mana": 35})
    assert "ฟื้น" in consumable_effect_hint(
        {"recovery_kind": "hp", "recovery_rank": "C"}
    )
    assert consumable_kind_tag({"heal_mana": 35}) == "ยาMP"
    assert consumable_kind_tag({"apply_status": "regen"}) == "บัฟ"


def test_menu_box_proportional():
    p = {"hp": 50, "max_hp": 100, "mana": 10, "max_mana": 40, "needs": {"fatigue": 60}}
    entries = [
        {"n": "1", "kind": "ยาHP", "name": "ยา HP", "effect": "HP+55"},
        {"n": "2", "kind": "ยาMP", "name": "ยา Mana", "effect": "MP+35"},
        {"n": "3", "kind": "บัฟ", "name": "ขี้ผึ้งฟื้นฟู", "effect": "บัฟ regen"},
    ]
    text = render_consumable_menu_box(entries, p, free_action=True)
    assert "ของใช้ในไฟต์" in text
    assert "HP+55" in text
    assert "ไม่เสียเทิร์น" in text
    assert "0 กลับ" in text or "0" in text
    for line in text.splitlines():
        assert display_width(line) <= 62


def test_care_hub_and_result_boxes():
    p = {"hp": 80, "max_hp": 194, "mana": 18, "max_mana": 100}
    hub = render_item_care_hub_box(p)
    assert "ยา / ล้าง / บัฟ" in hub
    assert "ไม่เสียเทิร์น" in hub
    res = render_item_use_result_box(
        name="ยา Mana",
        effect_lines=["ฟื้น MP +35  →  53/100"],
        free_action=True,
    )
    assert "ใช้ของแล้ว" in res
    assert "MP +35" in res
    assert "ไม่เสียเทิร์น" in res


def test_use_potion_shows_menu_box_and_result():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ciu", "warrior", "เมษ")
    recompute_stats(p, reg)
    ensure_needs(p)
    p["inventory"] = []
    p["inventory_ids"] = []
    p["inventory_rarities"] = []
    p["inventory_items"] = []
    p["mana"] = 10
    add_item(p, "potion_mana", reg)
    io = _IO(["1"])
    assert _use_potion(p, io, reg) is True
    text = io.joined()
    assert "ของใช้ในไฟต์" in text or "ยา" in text
    assert "ใช้ของแล้ว" in text or "MP" in text
    assert int(p["mana"]) > 10


def test_use_potion_cancel_zero():
    reg = DataRegistry.load(DATA_DIR)
    p = create_player(reg, "ci0", "warrior", "เมษ")
    recompute_stats(p, reg)
    p["inventory"] = []
    p["inventory_ids"] = []
    p["inventory_rarities"] = []
    add_item(p, "potion_hp", reg)
    before = list(p.get("inventory_ids") or [])
    io = _IO(["0"])
    assert _use_potion(p, io, reg) is False
    assert list(p.get("inventory_ids") or []) == before

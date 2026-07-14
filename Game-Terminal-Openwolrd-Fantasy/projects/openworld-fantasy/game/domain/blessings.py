"""
Rare level-up blessings — opaque weights, flavor first.
Players never see chances or formulas.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from game.data_load.registry import DataRegistry
from game.ports.io import IO


def _cfg(reg: Optional[DataRegistry]) -> Dict[str, Any]:
    if reg is None:
        return {}
    return dict(getattr(reg, "blessings", None) or {})


def ensure_blessing_fields(player: MutableMapping[str, Any]) -> None:
    player.setdefault("blessing_flags", [])
    player.setdefault("blessing_log", [])
    player.setdefault("emergency_blessings", [])
    player.setdefault("active_blessing_ids", [])


def try_level_up_blessing(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    io: Optional[IO] = None,
    levels: int = 1,
) -> List[str]:
    """
    Very rare roll per level gained. May present choice or store emergency.
    """
    ensure_blessing_fields(player)
    notes: List[str] = []
    cfg = _cfg(reg)
    base_chance = float(cfg.get("default_level_chance") or 0.04)
    table = list(cfg.get("blessings") or [])
    if not table:
        return notes

    for _ in range(max(1, int(levels))):
        # luck soft bias (hidden)
        luck = float(player.get("luck_score") or 0.0)
        chance = min(0.18, max(0.01, base_chance * (1.0 + luck * 0.5)))
        if rng.random() > chance:
            continue
        # weighted pick
        weights = [max(0.1, float(b.get("weight") or 1)) for b in table]
        total = sum(weights)
        r = rng.random() * total
        acc = 0.0
        pick = table[-1]
        for b, w in zip(table, weights):
            acc += w
            if r <= acc:
                pick = b
                break
        notes.extend(_apply_blessing(player, reg, pick, rng, io=io))
    return notes


def _apply_blessing(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    bless: Mapping[str, Any],
    rng: random.Random,
    *,
    io: Optional[IO] = None,
) -> List[str]:
    notes: List[str] = []
    bid = str(bless.get("id") or "unknown")
    name = str(bless.get("name") or bid)
    kind = str(bless.get("kind") or "passive")
    notes.append(f"✦ พรบางอย่างผ่านมา… 「{name}」")
    if bless.get("desc"):
        notes.append(f"  {bless.get('desc')}")

    if kind == "choice" and io is not None:
        choices = list(bless.get("choices") or [])
        if choices:
            io.write_line("\n── ทางแยกในใจ (ไม่รู้ว่าอันไหนดีกว่า) ──")
            for i, c in enumerate(choices, 1):
                io.write_line(f"  {i}. {c.get('label') or c.get('id')}")
            try:
                idx = int(io.read_line("เลือก: ").strip()) - 1
                ch = choices[max(0, min(len(choices) - 1, idx))]
            except Exception:
                ch = choices[0]
            _grant_flags(player, list(ch.get("flags") or []))
            notes.append(f"  คุณเลือกทางหนึ่ง… ผลยังไม่ชัด")
            player.setdefault("active_blessing_ids", []).append(bid)
            player.setdefault("blessing_log", []).append(bid)
            return notes

    if bless.get("store_emergency") or kind == "emergency":
        bag = list(player.get("emergency_blessings") or [])
        if bid not in bag:
            bag.append(bid)
            player["emergency_blessings"] = bag
            notes.append("  (เก็บความรู้สึกนี้ไว้ในใจ — อาจใช้ยามวิกฤต โดยไม่รู้เงื่อนไข)")
        player.setdefault("blessing_log", []).append(bid)
        return notes

    # passive
    _grant_flags(player, list(bless.get("flags") or []))
    if bless.get("learn_points"):
        player["learn_points"] = int(player.get("learn_points") or 0) + int(
            bless["learn_points"]
        )
        notes.append("  ความเข้าใจบางอย่างฝังลึกขึ้น…")
    if bless.get("luck_bias"):
        player["luck_score"] = float(player.get("luck_score") or 0) + float(
            bless["luck_bias"]
        )
    player.setdefault("active_blessing_ids", []).append(bid)
    player.setdefault("blessing_log", []).append(bid)
    return notes


def _grant_flags(player: MutableMapping[str, Any], flags: List[str]) -> None:
    bf = list(player.get("blessing_flags") or [])
    for f in flags:
        if f and f not in bf:
            bf.append(f)
    player["blessing_flags"] = bf
    if "quiet_mind" in flags or "grace_mind" in flags:
        player["intel_options"] = True


def try_emergency_blessing_menu(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    io: IO,
    *,
    reason: str = "วิกฤต",
) -> List[str]:
    """
    Rare opportunity when player is in danger — only if they hold emergency seed
    and soft roll passes. Conditions never explained.
    """
    ensure_blessing_fields(player)
    bag = list(player.get("emergency_blessings") or [])
    if not bag:
        return []
    cfg = _cfg(reg)
    ch = float(cfg.get("emergency_unlock_chance") or 0.12)
    luck = float(player.get("luck_score") or 0)
    if rng.random() > min(0.35, ch * (1.0 + luck)):
        return []
    bid = bag[0]
    io.write_line(f"\n…{reason}: ความรู้สึกเก่าๆ ผุดขึ้น — ใช้เมล็ดเอาชีวิตรอด? (y/n)")
    ans = io.read_line("เลือก: ").strip().lower()
    if ans not in ("y", "yes", "ใช่", "1"):
        return ["คุณปล่อยให้ความรู้สึกนั้นผ่านไป"]
    bag.pop(0)
    player["emergency_blessings"] = bag
    # soft rescue
    max_hp = int(player.get("max_hp") or 1)
    player["hp"] = max(int(player.get("hp") or 0), max(1, max_hp // 3))
    return ["✦ ร่างกายดึงตัวเองกลับมาได้ชั่วขณะ… (ไม่รู้ว่าทำไมได้)"]

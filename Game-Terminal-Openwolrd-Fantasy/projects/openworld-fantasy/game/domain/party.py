"""
Party system — max 3 companions.
Assist is automatic (relationship-gated chance). No mana/gold call cost.
Gifts/valuables build relationship; likes hidden (observe soft reactions).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry


MAX_PARTY = 3


def _cfg(reg: DataRegistry) -> Dict[str, Any]:
    return dict(getattr(reg, "party", None) or {})


def ensure_party(player: MutableMapping[str, Any]) -> List[Dict[str, Any]]:
    party = list(player.get("party") or [])
    player["party"] = party[:MAX_PARTY]
    player.setdefault("party_bonds", {})  # member_id -> bond int
    player.setdefault("party_calls", 0)
    # companions ever joined — can re-invite (P2)
    player.setdefault("party_known", [])  # list of template/member ids
    player.setdefault("party_known_meta", {})  # id -> {name, kind, joined, bond_peak}
    # old saves: current party → known roster (so re-invite works after dismiss)
    known = list(player.get("party_known") or [])
    meta = dict(player.get("party_known_meta") or {})
    bonds = player.get("party_bonds") or {}
    for m in player["party"]:
        if not isinstance(m, dict):
            continue
        mid = str(m.get("id") or "")
        if not mid:
            continue
        if mid not in known:
            known.append(mid)
        prev = dict(meta.get(mid) or {})
        bond_now = int(bonds.get(mid) or m.get("bond") or 1)
        meta[mid] = {
            "name": m.get("name") or prev.get("name") or mid,
            "kind": m.get("kind") or prev.get("kind") or "other",
            "joined": max(1, int(prev.get("joined") or 0)),
            "bond_peak": max(int(prev.get("bond_peak") or 0), bond_now),
            "template_id": m.get("template_id") or prev.get("template_id") or (
                mid if not mid.startswith("player:") else None
            ),
        }
    player["party_known"] = known
    player["party_known_meta"] = meta
    return player["party"]


def max_party_size(reg: DataRegistry) -> int:
    return int(_cfg(reg).get("max_party_size") or MAX_PARTY)


def party_size(player: Mapping[str, Any]) -> int:
    return len(player.get("party") or [])


def kind_label(reg: DataRegistry, kind_id: str) -> str:
    for k in _cfg(reg).get("kinds") or []:
        if str(k.get("id")) == kind_id:
            return str(k.get("name") or kind_id)
    return kind_id


def template_by_id(reg: DataRegistry, tid: str) -> Optional[Dict[str, Any]]:
    for t in _cfg(reg).get("templates") or []:
        if str(t.get("id")) == tid:
            return dict(t)
    return None


# ── Relationship (0–100) ─────────────────────────────────────────────

def _migrate_bond_value(raw: Any) -> int:
    """Old saves used small ints (0–10); new scale is 0–100."""
    try:
        v = int(raw or 0)
    except Exception:
        v = 0
    if v <= 12:
        return max(0, min(100, v * 10))
    return max(0, min(100, v))


def get_relationship(player: Mapping[str, Any], member_id: str, member: Optional[Mapping[str, Any]] = None) -> int:
    bonds = player.get("party_bonds") or {}
    mid = str(member_id)
    if mid in bonds:
        return _migrate_bond_value(bonds.get(mid))
    if member is not None:
        return _migrate_bond_value(member.get("bond") or member.get("relationship") or 12)
    return 12


def set_relationship(player: MutableMapping[str, Any], member_id: str, value: int) -> int:
    ensure_party(player)
    bonds = dict(player.get("party_bonds") or {})
    v = max(0, min(100, int(value)))
    bonds[str(member_id)] = v
    player["party_bonds"] = bonds
    # sync known meta peak
    meta = dict(player.get("party_known_meta") or {})
    e = dict(meta.get(str(member_id)) or {})
    e["bond_peak"] = max(int(e.get("bond_peak") or 0), v)
    meta[str(member_id)] = e
    player["party_known_meta"] = meta
    return v


def adjust_relationship(
    player: MutableMapping[str, Any],
    member_id: str,
    delta: float,
) -> int:
    cur = get_relationship(player, member_id)
    return set_relationship(player, member_id, int(round(cur + delta)))


def soft_relationship_label(score: int) -> str:
    s = int(score)
    if s >= 85:
        return "ผูกพันลึก"
    if s >= 65:
        return "ไว้ใจ"
    if s >= 45:
        return "คุ้นเคย"
    if s >= 25:
        return "รู้จัก"
    if s >= 10:
        return "ห่างเหิน"
    return "เย็นชา"


def relationship_bar(score: int, width: int = 8) -> str:
    s = max(0, min(100, int(score)))
    filled = int(round(s / 100.0 * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


# WO-PARTY-4: soft ceiling — high bond assists often, never "always"
ASSIST_CHANCE_SOFT_CAP = 0.90
# Soft mult clamp for assist damage (lighter than full player pipeline)
ASSIST_PIPE_CLAMP = (0.88, 1.12)
# Soft per-member damage ceiling vs base (anti runaway with 3 max bond)
ASSIST_HIT_SOFT_CAP_MULT = 2.4


def assist_chance_from_relationship(score: int) -> float:
    """Higher relationship → more frequent auto-assist (no player button)."""
    s = max(0, min(100, int(score)))
    # ~28% at 0 · ~55% at 40 · ~78% at 70 · ~90% soft-cap at 100 (WO-PARTY-4)
    return max(0.22, min(ASSIST_CHANCE_SOFT_CAP, 0.28 + s / 100.0 * 0.66))


def assist_chance_for_member(
    player: Mapping[str, Any],
    member_id: str,
    member: Optional[Mapping[str, Any]] = None,
) -> float:
    """
    WO-035.3: relationship primary + luck soft multiplier.
    WO-PARTY-4: soft-capped so bond 100 is not near-guaranteed every turn.
    Still no raw % shown to player.
    """
    rel = get_relationship(player, member_id, member)
    base = assist_chance_from_relationship(rel)
    luck = float(player.get("luck_score") or 0.0)
    # WO-036: luck soft only ±~6% relative — relationship stays primary
    mult = 1.0 + max(-0.08, min(0.08, luck * 0.22))
    return max(0.20, min(ASSIST_CHANCE_SOFT_CAP, base * mult))


def assist_pipeline_mult(
    player: Mapping[str, Any],
    mon: Optional[Mapping[str, Any]] = None,
    reg: Optional[Any] = None,
    *,
    kind: str = "beast",
) -> Tuple[float, Dict[str, Any]]:
    """
    WO-PARTY-4 Assist Pipeline Lite.

    Soft mult only — grade (outbound) + combat identity + kind lean.
    Does not rewrite full combat; no formula dump to player.
    """
    meta: Dict[str, Any] = {"source": "assist_lite"}
    mult = 1.0
    # Grade soft (same table spirit as damage_pipeline, full weight OK — already mild)
    try:
        from game.domain.damage_pipeline import grade_outbound_mult

        dmg_class = "arcane" if str(kind) in ("spirit", "heaven_god") else "physical"
        g_m, g_meta = grade_outbound_mult(player, dmg_class)
        # Assist uses half the grade edge (party is support, not main carry)
        edge = 1.0 + (float(g_m) - 1.0) * 0.55
        mult *= edge
        meta["grade"] = round(edge, 4)
        meta["grade_revealed"] = bool(g_meta.get("revealed"))
    except Exception:
        pass
    # Combat identity soft (tiny)
    try:
        from game.domain.combat_identity import identity_outbound_mult

        area = ""
        if reg is not None:
            area = str(player.get("location") or "")
        i_m, i_meta = identity_outbound_mult(player, mon=mon, area_id=area)
        # half identity edge
        i_edge = 1.0 + (float(i_m) - 1.0) * 0.50
        mult *= i_edge
        meta["identity"] = round(i_edge, 4)
        if i_meta:
            meta["id_keys"] = list(i_meta.keys())[:4]
    except Exception:
        pass
    # Soft mon toughness (elite/boss slightly resist raw assist spam)
    if mon is not None:
        if mon.get("boss"):
            mult *= 0.92
            meta["mon"] = "boss"
        elif mon.get("elite"):
            mult *= 0.96
            meta["mon"] = "elite"
    # Clamp
    lo, hi = ASSIST_PIPE_CLAMP
    mult = max(lo, min(hi, float(mult)))
    meta["final"] = round(mult, 4)
    return mult, meta


def _gift_like_tags_for_member(member: Mapping[str, Any], reg: Optional[DataRegistry] = None) -> List[str]:
    """Hidden preference tags — never listed in UI."""
    mid = str(member.get("id") or "")
    kind = str(member.get("kind") or "other")
    # template override
    if reg is not None:
        tpl = template_by_id(reg, mid) or {}
        if tpl.get("gift_likes"):
            return [str(x) for x in tpl.get("gift_likes") or []]
    by_kind = {
        "spirit": ["food", "incense", "rare", "arcane"],
        "beast": ["food", "material", "meat", "common"],
        "heaven_beast": ["food", "sacred", "shiny", "heaven"],
        "hell_beast": ["meat", "hell", "dark", "rare"],
        "heaven_god": ["sacred", "divine", "heaven", "gem", "shiny"],
        "hell_god": ["hell", "dark", "rare", "contract", "gem"],
        "other": ["rare", "material", "arcane", "shiny"],
        "player": ["food", "money", "rare", "shiny"],
    }
    tags = list(by_kind.get(kind, ["food", "material"]))
    # id-stable spice so individuals differ without data spam
    h = sum(ord(c) for c in mid) % 5
    extras = ["shiny", "gem", "food", "dark", "heaven"]
    tags.append(extras[h])
    return tags


def _item_gift_tags(item_id: str, item: Mapping[str, Any]) -> List[str]:
    tags: List[str] = []
    iid = str(item_id).lower()
    kind = str(item.get("kind") or "").lower()
    rar = str(item.get("rarity") or "common").lower()
    itags = [str(t).lower() for t in (item.get("tags") or [])]
    if is_foodish(item):
        tags.append("food")
        if "meat" in iid or "ration" in iid or "feast" in iid:
            tags.append("meat")
    if "incense" in iid or "ธูป" in str(item.get("name") or ""):
        tags.append("incense")
    if kind == "material" or "mat" in iid:
        tags.append("material")
    if rar in ("uncommon", "rare", "very_rare", "legendary", "sacred", "divine", "archdivine"):
        tags.append("rare")
        tags.append("shiny")
    if rar in ("sacred", "divine", "archdivine") or "bless" in iid or "heaven" in iid:
        tags.append("sacred")
        tags.append("heaven")
        tags.append("divine")
    if "hell" in iid or "void" in iid or "umbra" in iid or "shadow" in iid:
        tags.append("dark")
        tags.append("hell")
    if "contract" in iid:
        tags.append("contract")
    if "shard" in iid or "gem" in iid or "prism" in iid or "crystal" in iid:
        tags.append("gem")
        tags.append("shiny")
    if "arcane" in iid or "mana" in iid or "mind" in iid:
        tags.append("arcane")
    tags.extend(itags)
    price = int(item.get("price_world") or 0)
    if price >= 150:
        tags.append("valuable")
        tags.append("shiny")
    return list(dict.fromkeys(tags))


def is_foodish(item: Mapping[str, Any]) -> bool:
    try:
        from game.domain.needs import is_food_item

        return is_food_item(item)
    except Exception:
        tags = item.get("tags") or []
        return "food" in tags or str(item.get("kind") or "") == "food"


def evaluate_gift(
    member: Mapping[str, Any],
    item_id: str,
    item: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
) -> Tuple[str, int, str]:
    """
    Returns (tier, delta, soft_msg).
    tier: love | like | meh | dislike
    """
    likes = set(_gift_like_tags_for_member(member, reg))
    got = set(_item_gift_tags(item_id, item))
    overlap = likes & got
    price = int(item.get("price_world") or 0)
    rar = str(item.get("rarity") or "common").lower()

    if overlap & {"divine", "sacred", "heaven"} and likes & {"divine", "sacred", "heaven"}:
        return "love", 18, "…ดวงตาอ่อนลง ราวกับถูกเข้าใจ"
    if overlap & {"hell", "dark", "contract"} and likes & {"hell", "dark", "contract"}:
        return "love", 16, "…มันยิ้มแปลกๆ — ถูกใจอย่างชัด"
    if "food" in overlap and "food" in likes:
        return "like", 10, "…มันรับไปเงียบๆ บรรยากาศอุ่นขึ้น"
    if overlap & {"gem", "shiny", "valuable", "rare"}:
        return "like", 12 + (4 if price >= 200 else 0), "…ของสะท้อนแสง — มันสนใจ"
    if overlap:
        return "like", 8, "…มันพยักน้อยๆ"
    if rar in ("common",) and price < 30:
        return "meh", 2, "…รับไว้ แต่ไม่ตื่นเต้น"
    if "food" in got and "food" not in likes:
        return "meh", 3, "…กิน/ดมแล้วหันไป"
    # disliked if strongly opposing
    if ("heaven" in got or "sacred" in got) and likes & {"hell", "dark"}:
        return "dislike", -4, "…มันเบือนหน้า — ไม่ถูกโทน"
    if ("hell" in got or "dark" in got) and likes & {"heaven", "sacred"}:
        return "dislike", -4, "…แสงรอบตัวมันหด — ไม่ชอบ"
    return "meh", 3, "…รับไปโดยไม่บอกเหตุผล"


def give_item_gift(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    member_index: int,
    inv_index: int,
) -> List[str]:
    """
    Give inventory item to party member — builds/hides relationship.

    WO-PARTY-3: remove exactly **1 unit** from a stack (True Stack safe).
    Does not strip the whole slot when qty > 1.
    """
    ensure_party(player)
    party = list(player.get("party") or [])
    if member_index < 0 or member_index >= len(party):
        return ["ไม่มีสมาชิกช่องนั้น"]
    ids = list(player.get("inventory_ids") or [])
    if inv_index < 0 or inv_index >= len(ids):
        return ["ไม่มีของช่องนั้น"]
    m = party[member_index]
    mid = str(m.get("id"))
    iid = str(ids[inv_index])
    it = dict((reg.items or {}).get(iid) or {"id": iid, "name": iid})
    # WO-PARTY-3: one unit only (stack-aware)
    removed = None
    try:
        from game.domain.bag_stack import qty_at, remove_units_at

        have = qty_at(player, inv_index)
        if have < 1:
            return ["ไม่มีของช่องนั้น"]
        removed = remove_units_at(player, inv_index, reg, amount=1)
    except Exception:
        removed = None
    if not removed:
        # fallback: single non-stack slot
        try:
            from game.domain.rarity import remove_inventory_at_index

            ids_now = list(player.get("inventory_ids") or [])
            if inv_index < 0 or inv_index >= len(ids_now):
                return ["ไม่มีของช่องนั้น"]
            if str(ids_now[inv_index]) != iid:
                # index shifted — re-find first matching id
                try:
                    inv_index = ids_now.index(iid)
                except ValueError:
                    return ["ของหายไปแล้ว"]
            popped = remove_inventory_at_index(player, inv_index, reg)
            if not popped:
                return ["ไม่มีของช่องนั้น"]
            removed = (str(popped[0]), str(popped[1]), 1)
        except Exception:
            ids = list(player.get("inventory_ids") or [])
            if inv_index < 0 or inv_index >= len(ids):
                return ["ไม่มีของช่องนั้น"]
            ids.pop(inv_index)
            player["inventory_ids"] = ids
            removed = (iid, "common", 1)
    tier, delta, soft = evaluate_gift(m, iid, it, reg)
    # value bonus
    price = int(it.get("price_world") or 0)
    if tier in ("love", "like") and price >= 100:
        delta += min(8, price // 80)
    before = get_relationship(player, mid, m)
    after = adjust_relationship(player, mid, delta)
    name = m.get("name") or mid
    iname = it.get("name") or iid
    notes = [
        f"คุณยื่น「{iname}」ให้ {name}",
        f" {soft}",
        f" สัมพันธ์สหาย [{relationship_bar(after)}] {soft_relationship_label(after)}",
    ]
    if after > before + 10:
        notes.append(" …รู้สึกใกล้ชิดขึ้นชัดเจน")
    elif after < before:
        notes.append(" …บรรยากาศเย็นลงนิด")
    # WO-PARTY-5: sharing food soft-eases player hunger (companions "share the meal")
    try:
        from game.domain.needs import apply_food_relief, is_food_item

        if is_food_item(it):
            hr = max(4, min(14, int(it.get("hunger_relief") or 12) // 3))
            fr = max(0, min(4, int(it.get("fatigue_relief") or 2) // 2))
            mb = max(1, min(5, int(it.get("morale_boost") or 3) // 2))
            soft_n = apply_food_relief(
                player,
                hunger_relief=hr,
                fatigue_relief=fr,
                morale_boost=mb,
                silent=True,
            )
            notes.append(" …แบ่งคำ — ท้อง/ขวัญเบาขึ้นนิด")
            for sn in soft_n[:1]:
                if sn and "สถานะ" not in sn:
                    notes.append(f" {sn}")
    except Exception:
        pass
    return notes


def give_money_gift(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    member_index: int,
    *,
    currency: str = "world",
    amount: int = 0,
) -> List[str]:
    """Offer money_world / heaven / hell as gift (valuables)."""
    ensure_party(player)
    party = list(player.get("party") or [])
    if member_index < 0 or member_index >= len(party):
        return ["ไม่มีสมาชิกช่องนั้น"]
    m = party[member_index]
    mid = str(m.get("id"))
    key = {
        "world": "money_world",
        "heaven": "money_heaven",
        "hell": "money_hell",
    }.get(currency, "money_world")
    have = int(player.get(key) or 0)
    amt = max(0, int(amount))
    if amt <= 0 or have < amt:
        return ["เงินไม่พอ"]
    player[key] = have - amt
    likes = set(_gift_like_tags_for_member(m, reg))
    soft_map = {
        "world": ("money", "shiny"),
        "heaven": ("heaven", "sacred", "shiny"),
        "hell": ("hell", "dark", "valuable"),
    }
    tags = set(soft_map.get(currency, ("money",)))
    if tags & likes:
        delta = 6 + min(14, amt // (5 if currency != "world" else 25))
        msg = "…มันพึงพอใจกับของมีค่านี้"
    else:
        delta = 2 + min(6, amt // (8 if currency != "world" else 40))
        msg = "…รับไว้โดยไม่แสดงออกมาก"
    after = adjust_relationship(player, mid, delta)
    label = {"world": "เงินโลก", "heaven": "เงินสวรรค์", "hell": "เงินนรก"}.get(currency, "เงิน")
    return [
        f"คุณมอบ{label} {amt} ให้ {m.get('name')}",
        f" {msg}",
        f" สัมพันธ์สหาย [{relationship_bar(after)}] {soft_relationship_label(after)}",
    ]


def tick_relationship_decay(player: MutableMapping[str, Any], *, ticks: int = 1) -> None:
    """
    Very slow decay for companions not currently in the active party.
    ~0.12 point per field/dungeon tick (fractional debt → ~1 pt / 8–9 ticks).
    Floor at 5 — never forgotten quickly. Active party members do not decay.
    """
    ensure_party(player)
    active = {str(m.get("id")) for m in (player.get("party") or [])}
    bonds = dict(player.get("party_bonds") or {})
    debt = dict(player.get("party_bond_decay_debt") or {})
    changed = False
    for mid, raw in list(bonds.items()):
        if mid in active:
            # reset fractional debt while together
            if mid in debt:
                debt.pop(mid, None)
                changed = True
            continue
        cur = _migrate_bond_value(raw)
        if cur <= 5:
            continue
        # accumulate fractional decay so int bonds still drop slowly
        d = float(debt.get(mid) or 0.0) + 0.12 * max(1, int(ticks))
        drop = int(d)
        if drop > 0:
            d -= float(drop)
            nxt = max(5, cur - drop)
            if nxt != cur:
                bonds[mid] = nxt
                changed = True
        debt[mid] = round(d, 4)
        changed = True
    if changed:
        player["party_bonds"] = bonds
        player["party_bond_decay_debt"] = debt


def format_party_panel(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_party(player)  # type: ignore
    mx = max_party_size(reg)
    lines = [f"── ปาร์ตี้ ({party_size(player)}/{mx}) ──"]
    lines.append("  (สัมพันธ์สหาย ≠ เรโซแนนซ์เรลิก)")
    party = list(player.get("party") or [])
    if not party:
        lines.append("  ว่าง — ต้องได้รับการยอมรับจึงร่วมทีมได้")
        lines.append("  เงาในโลกอาจยื่นมือมาเมื่อคุณเดินทาง/สำรวจ…")
        lines.append("  สร้างสัมพันธ์สหายด้วยของขวัญ/ของมีค่า (ชอบอะไร — สังเกตเอง)")
        known = list(player.get("party_known") or [])
        if known:
            lines.append(f"  สหายที่เคยร่วมทาง: {len(known)} ตน — Y เชิญกลับได้")
        return lines
    for i, m in enumerate(party, 1):
        kind = kind_label(reg, str(m.get("kind") or "other"))
        name = m.get("name") or m.get("id")
        mid = str(m.get("id"))
        rel = get_relationship(player, mid, m)
        soft = soft_relationship_label(rel)
        bar = relationship_bar(rel)
        rlab = m.get("rarity_label") or m.get("rarity") or ""
        rbit = f" · {rlab}" if rlab else ""
        lines.append(f"  {i}. {name} · {kind}{rbit}")
        # WO-PARTY-6: explicit สัมพันธ์สหาย label (no raw score in soft UI)
        lines.append(f"     สัมพันธ์สหาย [{bar}] {soft}")
        try:
            from game.domain.appraisal import format_party_appraisal_blurb

            lines.append(f"     {format_party_appraisal_blurb(player, m, reg)}")
        except Exception:
            pass
        if m.get("flavor"):
            lines.append(f"     “{m.get('flavor')}”")
    lines.append("  ไฟต์: ซุ่มช่วยอัตโน (โอกาสตามสัมพันธ์สหาย) · ไม่เสียมานา/เงิน")
    lines.append("  Y: ของขวัญ · อ่านสหาย (soft) · เชิญกลับ")
    known_n = len(player.get("party_known") or [])
    if known_n:
        lines.append(f"  รู้จักสหาย {known_n} ตน — เชิญกลับได้ (นอกทีม bond ลดช้ามาก)")
    if player.get("unit_class_id"):
        from game.domain.unit_system import soft_mastery_label

        lines.append(
            f"  Unit: {player.get('unit_class_name')} · "
            f"{soft_mastery_label(int(player.get('unit_mastery') or 0))}"
        )
    return lines


def _has_slot(player: Mapping[str, Any], reg: DataRegistry) -> bool:
    return party_size(player) < max_party_size(reg)


def _already_in(player: Mapping[str, Any], mid: str) -> bool:
    return any(str(m.get("id")) == mid for m in (player.get("party") or []))


def can_recruit_template(
    player: Mapping[str, Any],
    reg: DataRegistry,
    template: Mapping[str, Any],
    *,
    affinity: float = 0.5,
) -> Tuple[bool, str]:
    """Hidden checks — messages stay vague."""
    if not _has_slot(player, reg):
        return False, "ทีมเต็มแล้ว (สูงสุด 3)"
    tid = str(template.get("id"))
    if _already_in(player, tid):
        return False, "อยู่ร่วมทางอยู่แล้ว"
    if int(player.get("level", 1)) < int(template.get("min_level") or 1):
        return False, "ยังไม่พร้อมเดินด้วยกัน"
    need = float(template.get("affinity_need") or 0)
    if affinity < need:
        return False, "มันยังไม่ยอมรับคุณ"
    area = str(player.get("location") or "")
    req_area = template.get("require_area")
    if req_area and area != req_area:
        return False, "ที่นี่ไม่ใช่ที่ของมัน"
    st = player.get("stats") or {}
    if int(st.get("boss_kills", 0)) < int(template.get("require_boss_kills") or 0):
        return False, "ยังขาดบางอย่างที่มันมองหา"
    if int(st.get("deaths", 0)) < int(template.get("require_deaths") or 0):
        return False, "เส้นทางของคุณยังตื้นเกินไป"
    lib = len(player.get("library_entries_read") or [])
    if lib < int(template.get("require_library") or 0):
        return False, "ความรู้ยังไม่พอให้มันเชื่อ"
    if int(player.get("money_heaven", 0)) < int(template.get("require_money_heaven") or 0):
        return False, "ขาดของจากสวรรค์"
    if int(player.get("money_hell", 0)) < int(template.get("require_money_hell") or 0):
        return False, "ขาดของจากนรก"
    # hire costs are checked at attempt_join (may partially pay on fail)
    return True, "ok"


def add_member(player: MutableMapping[str, Any], member: Dict[str, Any], reg: DataRegistry) -> str:
    ensure_party(player)
    if not _has_slot(player, reg):
        return "ปาร์ตี้เต็ม (สูงสุด 3)"
    mid = str(member.get("id") or "")
    if not mid or _already_in(player, mid):
        return "มีสมาชิกนี้อยู่แล้ว"
    party = list(player["party"])
    party.append(member)
    player["party"] = party
    bonds = dict(player.get("party_bonds") or {})
    bonds[mid] = int(member.get("bond") or 1)
    player["party_bonds"] = bonds
    mark_known_companion(player, member)
    return f"✦ {member.get('name')} ยอมร่วมทางแล้ว ({kind_label(reg, str(member.get('kind')))})"


def remove_member(player: MutableMapping[str, Any], index: int) -> str:
    ensure_party(player)
    party = list(player["party"])
    if index < 0 or index >= len(party):
        return "ไม่มีสมาชิกช่องนั้น"
    m = party.pop(index)
    player["party"] = party
    # stay in known roster for re-invite
    mark_known_companion(player, m)
    return f"{m.get('name')} แยกทางไป... (ยังจำคุณได้ — อาจเชิญกลับได้)"


def member_from_template(
    template: Mapping[str, Any],
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
    *,
    rarity: Optional[str] = None,
) -> Dict[str, Any]:
    from game.domain.rarity import rarity_label, roll_rarity, scale_stat

    kind = str(template.get("kind") or "other")
    rid = rarity
    if not rid:
        if template.get("rarity"):
            rid = str(template["rarity"])
        elif reg is not None:
            rng = rng or random.Random()
            # higher kinds can roll higher max
            max_rank = {
                "heaven_god": 8,
                "hell_god": 8,
                "heaven_beast": 6,
                "hell_beast": 6,
                "spirit": 5,
                "beast": 5,
                "other": 6,
            }.get(kind, 5)
            rid = roll_rarity(reg, rng, kind=kind, pool="recruit", max_rank=max_rank)
        else:
            rid = "common"
    base_atk = int(template.get("bonus_atk") or 0)
    base_hp = int(template.get("bonus_max_hp") or 0)
    base_mp = int(template.get("bonus_max_mana") or 0)
    return {
        "id": str(template.get("id")),
        "name": template.get("name"),
        "kind": kind,
        "source": "template",
        "template_id": str(template.get("id")),
        "role": str(template.get("role") or template.get("assist_role") or ""),
        "rarity": rid,
        "rarity_label": rarity_label(reg, rid) if reg else rid,
        "bonus_atk": scale_stat(base_atk, rid, reg),
        "bonus_max_hp": scale_stat(base_hp, rid, reg),
        "bonus_max_mana": scale_stat(base_mp, rid, reg),
        "call_mana": int(template.get("call_mana") or 4),
        "call_world": int(template.get("call_world") or 0),
        "call_heaven": int(template.get("call_heaven") or 0),
        "call_hell": int(template.get("call_hell") or 0),
        "flavor": template.get("flavor") or "",
        "bond": 1,
    }


def member_from_player_echo(
    other: Mapping[str, Any],
    affinity: float,
    reg: Optional[DataRegistry] = None,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Hire another world's player — stats scaled soft, never show raw numbers."""
    from game.domain.rarity import rarity_label, roll_rarity, scale_stat

    atk = max(1, int(other.get("bonus_atk") or 5) // 4)
    hp = max(5, int(other.get("max_hp") or 80) // 12)
    mp = max(2, int(other.get("max_mana") or 40) // 10)
    rid = "common"
    if reg is not None:
        rng = rng or random.Random()
        rid = roll_rarity(reg, rng, kind="player", pool="recruit", max_rank=5)
    atk = scale_stat(atk + (1 if affinity > 0.4 else 0), rid, reg, floor=1)
    hp = scale_stat(hp, rid, reg, floor=1)
    mp = scale_stat(mp, rid, reg, floor=1)
    return {
        "id": f"player:{other.get('id') or other.get('name')}",
        "name": other.get("name") or "ผู้พเนจร",
        "kind": "player",
        "source": "player_echo",
        "ref_player_id": other.get("id"),
        "rarity": rid,
        "rarity_label": rarity_label(reg, rid) if reg else rid,
        "bonus_atk": atk,
        "bonus_max_hp": hp,
        "bonus_max_mana": mp,
        "call_mana": 5 + max(0, 3 - int(affinity * 5)),
        "call_world": 10 if affinity < 0.3 else 0,
        "call_heaven": 0,
        "call_hell": 0,
        "flavor": f"สาย {(other.get('occ_path') or other.get('occupation') or '???')}",
        "bond": 1 if affinity < 0.5 else 2,
        "affinity_at_hire": round(affinity, 3),
    }


def try_consent_player_hire(
    player: Mapping[str, Any],
    other: Mapping[str, Any],
    reg: DataRegistry,
    affinity: float,
    rng: random.Random,
) -> Tuple[bool, str]:
    """Hidden consent roll — need acceptance, not automatic."""
    if not _has_slot(player, reg):
        return False, "ทีมเต็ม — เขาพยักหน้าแล้วจาก"
    if _already_in(player, f"player:{other.get('id')}"):
        return False, "ร่วมทางอยู่แล้ว"
    base = float(_cfg(reg).get("player_hire_base_chance") or 0.35)
    # better affinity → easier consent; foe path hard
    chance = base + max(-0.25, min(0.45, affinity * 0.4))
    if affinity < -0.2:
        return False, "เขาปฏิเสธเด็ดขาด"
    if rng.random() > chance:
        return False, "เขายังไม่ยอมรับการร่วมทีม... (ต้องลองสร้างความสัมพันธ์)"
    return True, "ok"


def try_recruit_template_offer(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
    *,
    affinity: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Maybe offer a template companion after explore/sight — conditions hidden."""
    if not _has_slot(player, reg):
        return None
    templates = list(_cfg(reg).get("templates") or [])
    if not templates:
        return None
    rng.shuffle(templates)
    aff = float(affinity if affinity is not None else 0.3 + rng.random() * 0.4)
    for t in templates:
        ok, _ = can_recruit_template(player, reg, t, affinity=aff)
        if ok and rng.random() < 0.45:
            return dict(t)
    return None


def party_passive_bonuses(player: Mapping[str, Any]) -> Dict[str, int]:
    """Always-on soft bonuses from party (smaller than call)."""
    atk = hp = mp = 0
    for m in player.get("party") or []:
        atk += max(0, int(m.get("bonus_atk") or 0) // 2)
        hp += max(0, int(m.get("bonus_max_hp") or 0) // 3)
        mp += max(0, int(m.get("bonus_max_mana") or 0) // 3)
    return {"atk": atk, "max_hp": hp, "max_mana": mp}


def apply_party_passives_to_player(player: MutableMapping[str, Any], reg: DataRegistry) -> None:
    """Store party passive deltas for recompute (non-destructive base)."""
    ensure_party(player)
    b = party_passive_bonuses(player)
    player["party_bonus_atk"] = b["atk"]
    player["party_bonus_max_hp"] = b["max_hp"]
    player["party_bonus_max_mana"] = b["max_mana"]


def call_party_power(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    member_index: int,
) -> Tuple[bool, str, Dict[str, int]]:
    """
    Combat menu 5: no mana/gold cost.
    Relationship status + optional free focus if bond high.
    Assists are automatic (party_member_turns).
    """
    ensure_party(player)
    party = list(player.get("party") or [])
    if member_index < 0 or member_index >= len(party):
        return False, "ไม่มีสมาชิก", {}
    m = party[member_index]
    mid = str(m.get("id"))
    name = m.get("name") or mid
    rel = get_relationship(player, mid, m)
    bar = relationship_bar(rel)
    lab = soft_relationship_label(rel)
    bonuses: Dict[str, int] = {"atk": 0, "max_hp": 0, "max_mana": 0}
    if rel >= 40 and not player.get("_party_focus_used"):
        bonuses["atk"] = max(1, int(m.get("bonus_atk") or 1) // 2)
        player["bonus_atk"] = int(player.get("bonus_atk") or 0) + bonuses["atk"]
        pend = list(player.get("party_call_active") or [])
        pend.append({"id": f"focus:{mid}", **bonuses})
        player["party_call_active"] = pend
        player["_party_focus_used"] = True
        adjust_relationship(player, mid, 1)
        msg = (
            f"「{name}」สัมพันธ์สหาย [{bar}] {lab} — ซุ่มอัตโน · "
            f"โฟกัสเบา (ไม่เสียมานา/เงิน)"
        )
        return True, msg, bonuses
    msg = (
        f"「{name}」สัมพันธ์สหาย [{bar}] {lab} — ช่วยเมื่อจังหวะถึง "
        f"(ตาม bond สหาย · ไม่กด · ไม่เสียทรัพยากร)"
    )
    return True, msg, bonuses



def party_assist_damage(
    player: Mapping[str, Any],
    mon: MutableMapping[str, Any],
    rng: random.Random,
    reg: Optional[Any] = None,
) -> List[str]:
    """Backward-compatible alias → party_member_turns (full soft AI). """
    return party_member_turns(player, mon, rng, reg)  # type: ignore[arg-type]


def party_member_turns(
    player: MutableMapping[str, Any],
    mon: MutableMapping[str, Any],
    rng: random.Random,
    reg: Optional[Any] = None,
) -> List[str]:
    """
    Soft full party turns after the player acts.
    WO-PARTY-7: Priority Decision Engine (heal/cleanse/attack/buff) + soft fail.
    Same path for Auto Play.
    """
    from game.domain.companion_decision_engine import (
        ACT_ATTACK,
        ACT_BUFF,
        ACT_CLEANSE,
        ACT_HEAL,
        ACT_WAIT,
        decide,
        success_chance,
    )

    notes: List[str] = []
    party = list(player.get("party") or [])
    if not party or int(mon.get("hp", 0)) <= 0:
        return notes
    notes.append("  ── ซุ่มช่วย (ตามสัมพันธ์สหาย) ──")
    acted_any = False
    team_cleansed = False  # at most one cleanse attempt success per player turn
    for m in party:
        if int(mon.get("hp", 0)) <= 0:
            break
        if not isinstance(m, dict):
            continue
        mid = str(m.get("id"))
        rel = get_relationship(player, mid, m)
        try:
            chance = assist_chance_for_member(player, mid, m)
        except Exception:
            chance = assist_chance_from_relationship(rel)
        if rng.random() > chance:
            continue
        acted_any = True
        name = m.get("name") or mid
        kind = str(m.get("kind") or "")
        base = max(1, int(m.get("bonus_atk") or 2))
        rel_pow = 0.85 + (rel / 100.0) * 0.60
        mon_ratio = int(mon.get("hp") or 0) / max(1, int(mon.get("max_hp") or 1))

        decision = decide(
            player,
            mon,
            m,
            bond=rel,
            reg=reg,
            team_cleansed_this_round=team_cleansed,
        )
        action = str(decision.action or ACT_ATTACK)
        if action == ACT_WAIT:
            notes.append(f"  › {name} ยังรอดู…")
            continue

        # soft success roll (especially cleanse)
        sc = success_chance(player, m, action=action, bond=rel, reg=reg)
        ok = rng.random() < sc

        if action == ACT_CLEANSE:
            if team_cleansed:
                # already cleansed this round — fall through to heal/attack
                action = ACT_HEAL if int(player.get("hp") or 0) < int(player.get("max_hp") or 1) * 0.7 else ACT_ATTACK
            elif not ok:
                notes.append(f"  › {name} พยายามชำระอาการ… แต่แรงยังไม่พอ")
                try:
                    from game.domain.alerts import emit_alert_lines

                    notes.extend(
                        emit_alert_lines(
                            player,
                            "party.assist_fail",
                            force=False,
                            name=str(name),
                        )
                    )
                except Exception:
                    pass
                continue
            else:
                target = str(decision.cleanse_target or "poison")
                try:
                    from game.domain.status_fx import cleanse, has_status

                    if not has_status(player, target) and target != "all_debuffs":
                        # try poison fallback
                        if has_status(player, "poison"):
                            target = "poison"
                    cleared = cleanse(player, reg, mode=target)
                    team_cleansed = True
                    if cleared:
                        notes.append(f"  › {name} ชำระ「{target}」ให้คุณ — อาการเบาขึ้น")
                    else:
                        notes.append(f"  › {name} แผ่แสงชำระ… (อาการบางอย่างจางลง)")
                    try:
                        from game.domain.alerts import emit_alert_lines

                        notes.extend(
                            emit_alert_lines(
                                player,
                                "party.assist_cleanse_ok",
                                force=False,
                                name=str(name),
                                ailment=target,
                            )
                        )
                    except Exception:
                        pass
                except Exception:
                    notes.append(f"  › {name} พยายามชำระ…")
                if rng.random() < 0.10:
                    adjust_relationship(player, mid, 1)
                continue

        if action == ACT_HEAL:
            if not ok and rng.random() < 0.35:
                notes.append(f"  › {name} ยื่นมือรักษา — ยังแผ่ว")
                continue
            heal = max(
                2,
                int(round(base * (1.2 + rel / 100.0) * rel_pow + rng.randint(1, 4))),
            )
            player["hp"] = min(
                int(player.get("max_hp") or heal), int(player.get("hp") or 0) + heal
            )
            notes.append(f"  › {name} ซุ่มรักษา → HP +{heal}")
            try:
                from game.domain.needs import ensure_needs, get_needs

                ensure_needs(player)
                n = dict(player.get("needs") or get_needs(player))
                n["fatigue"] = max(0, int(n.get("fatigue") or 0) - max(1, 1 + rel // 40))
                n["morale"] = min(100, int(n.get("morale") or 50) + max(1, 1 + rel // 50))
                player["needs"] = n
                if rng.random() < 0.22:
                    notes.append("  › ขวัญอุ่นขึ้นเล็กน้อย…")
            except Exception:
                pass
        elif action == ACT_BUFF:
            boost = max(1, int(round((base // 3) * rel_pow)))
            player["bonus_atk"] = int(player.get("bonus_atk") or 0) + boost
            pend = list(player.get("party_call_active") or [])
            pend.append(
                {"id": f"softbuff:{mid}", "atk": boost, "max_hp": 0, "max_mana": 0}
            )
            player["party_call_active"] = pend
            notes.append(f"  › {name} ซุ่มเสริมพลัง (ชั่วคราว)")
        else:
            # attack (default)
            finish_mult = 1.0
            if mon_ratio <= 0.25:
                finish_mult = 1.12 + (0.08 if mon.get("elite") or mon.get("boss") else 0.0)
            kmult = {
                "player": 1.15,
                "beast": 1.2,
                "hell_beast": 1.25,
                "heaven_beast": 1.1,
                "heaven_god": 1.35,
                "hell_god": 1.4,
                "spirit": 0.95,
            }.get(kind, 1.0)
            pipe_m, pipe_meta = assist_pipeline_mult(player, mon, reg, kind=kind)
            raw = (
                base
                * kmult
                * rel_pow
                * finish_mult
                * pipe_m
                * (0.85 + rng.random() * 0.55)
            )
            cap = max(2.0, float(base) * ASSIST_HIT_SOFT_CAP_MULT * rel_pow)
            dmg = max(1, int(round(min(raw, cap))))
            mon["hp"] = int(mon.get("hp", 0)) - dmg
            try:
                from game.domain.narrative import narrate

                flavor = narrate(reg, "party_assist", rng, name=name, dmg=dmg)
                if flavor:
                    notes.extend(flavor)
                else:
                    notes.append(f"  › {name} ซุ่มโจมตี → {dmg}")
            except Exception:
                notes.append(f"  › {name} ซุ่มโจมตี → {dmg}")
            if (
                reg is not None
                and float(pipe_meta.get("final") or 1.0) >= 1.04
                and rng.random() < 0.12
            ):
                notes.append("  › จังหวะซุ่มสอดกับฝีมือคุณ…")
            if int(mon.get("hp", 0)) <= 0:
                notes.append(f"  › {name} ปิดงาน!")
                break
        if rng.random() < 0.10:
            adjust_relationship(player, mid, 1)
    if not acted_any:
        notes.append("  › ทีมยังรอดูจังหวะ… (สัมพันธ์ยิ่งสูง ยิ่งซุ่มบ่อย)")
    return notes


def clear_party_call_buffs(player: MutableMapping[str, Any]) -> None:
    """Remove temporary call bonuses after combat (best-effort)."""
    active = list(player.get("party_call_active") or [])
    if not active:
        return
    for b in active:
        player["bonus_atk"] = max(0, int(player.get("bonus_atk", 0)) - int(b.get("atk") or 0))
        # max_hp/mana reductions careful of current hp
        player["max_hp"] = max(10, int(player.get("max_hp", 10)) - int(b.get("max_hp") or 0))
        player["hp"] = min(int(player["hp"]), int(player["max_hp"]))
        player["max_mana"] = max(0, int(player.get("max_mana", 0)) - int(b.get("max_mana") or 0))
        player["mana"] = min(int(player.get("mana", 0)), int(player["max_mana"]))
    player["party_call_active"] = []




# ── P1–P3: known roster · tier hire · consent ─────────────────────────

def mark_known_companion(player: MutableMapping[str, Any], member: Mapping[str, Any]) -> None:
    """Remember companion for soft re-invite (never shows formulas)."""
    player.setdefault("party_known", [])
    player.setdefault("party_known_meta", {})
    player.setdefault("party_bonds", {})
    mid = str(member.get("id") or "")
    if not mid:
        return
    known = list(player.get("party_known") or [])
    if mid not in known:
        known.append(mid)
    player["party_known"] = known
    meta = dict(player.get("party_known_meta") or {})
    prev = dict(meta.get(mid) or {})
    joined = int(prev.get("joined") or 0) + 1
    bond_now = int((player.get("party_bonds") or {}).get(mid) or member.get("bond") or 1)
    peak = max(int(prev.get("bond_peak") or 0), bond_now)
    meta[mid] = {
        "name": member.get("name") or prev.get("name") or mid,
        "kind": member.get("kind") or prev.get("kind") or "other",
        "joined": joined,
        "bond_peak": peak,
        "template_id": member.get("template_id") or (
            mid if not str(mid).startswith("player:") else prev.get("template_id")
        ),
    }
    player["party_known_meta"] = meta


def template_tier(template: Mapping[str, Any]) -> int:
    """
    Hidden difficulty tier 0–3 for hire/consent scaling.
    Explicit template.tier wins; else from kind + min_level.
    """
    if template.get("tier") is not None:
        return max(0, min(3, int(template.get("tier") or 0)))
    kind = str(template.get("kind") or "other")
    lv = int(template.get("min_level") or 1)
    base = {
        "spirit": 0,
        "beast": 0,
        "heaven_beast": 2,
        "hell_beast": 2,
        "heaven_god": 3,
        "hell_god": 3,
        "other": 2,
        "player": 1,
    }.get(kind, 1)
    if lv >= 28:
        base = max(base, 3)
    elif lv >= 18:
        base = max(base, 2)
    elif lv >= 10:
        base = max(base, 1)
    return max(0, min(3, base))


def hire_cost_table(template: Mapping[str, Any]) -> Dict[str, int]:
    """Costs to request join (world/heaven/hell). Explicit fields override tier defaults."""
    tier = template_tier(template)
    defaults = {
        0: {"world": 0, "heaven": 0, "hell": 0},
        1: {"world": 25, "heaven": 0, "hell": 0},
        2: {"world": 40, "heaven": 1, "hell": 1},
        3: {"world": 80, "heaven": 2, "hell": 2},
    }
    d = dict(defaults.get(tier) or defaults[1])
    # kind-specific money realm
    kind = str(template.get("kind") or "")
    if kind in ("heaven_beast", "heaven_god") and d["heaven"] == 0 and tier >= 2:
        d["heaven"] = max(1, tier - 1)
        d["hell"] = 0
    if kind in ("hell_beast", "hell_god") and d["hell"] == 0 and tier >= 2:
        d["hell"] = max(1, tier - 1)
        d["heaven"] = 0
    # explicit overrides
    if template.get("hire_world") is not None:
        d["world"] = int(template.get("hire_world") or 0)
    if template.get("hire_heaven") is not None:
        d["heaven"] = int(template.get("hire_heaven") or 0)
    if template.get("hire_hell") is not None:
        d["hell"] = int(template.get("hire_hell") or 0)
    # also count require_money as part of presence (not double-charged if hire covers)
    return d


def can_afford_hire(player: Mapping[str, Any], costs: Mapping[str, int]) -> Tuple[bool, str]:
    if int(player.get("money_world") or 0) < int(costs.get("world") or 0):
        return False, "ทรัพยากรยังไม่พอให้มันสนใจ (โลก?)"
    if int(player.get("money_heaven") or 0) < int(costs.get("heaven") or 0):
        return False, "ยังขาดสิ่งจากสวรรค์"
    if int(player.get("money_hell") or 0) < int(costs.get("hell") or 0):
        return False, "ยังขาดสิ่งจากนรก"
    return True, "ok"


def pay_hire(
    player: MutableMapping[str, Any],
    costs: Mapping[str, int],
    *,
    fraction: float = 1.0,
) -> List[str]:
    """Pay hire costs; fraction < 1 for soft fail tax."""
    notes: List[str] = []
    f = max(0.0, min(1.0, float(fraction)))
    for key, label in (
        ("world", "money_world"),
        ("heaven", "money_heaven"),
        ("hell", "money_hell"),
    ):
        amt = int(round(int(costs.get(key) or 0) * f))
        if amt <= 0:
            continue
        pkey = label
        have = int(player.get(pkey) or 0)
        lose = min(have, amt)
        player[pkey] = have - lose
        if lose:
            soft = {"world": "เงินโลก", "heaven": "เงินสวรรค์", "hell": "เงินนรก"}[key]
            notes.append(f"  ใช้{soft} {lose}")
    return notes


def consent_chance(
    template: Mapping[str, Any],
    affinity: float,
    *,
    bond_peak: int = 0,
    known: bool = False,
) -> float:
    """Hidden probability of accepting join request."""
    tier = template_tier(template)
    base = {0: 0.72, 1: 0.55, 2: 0.38, 3: 0.22}.get(tier, 0.5)
    need = float(template.get("affinity_need") or 0.2)
    # how far above need
    surplus = max(0.0, float(affinity) - need)
    base += min(0.28, surplus * 0.5)
    if known:
        base += 0.12 + min(0.15, bond_peak * 0.03)
    # clamp
    return max(0.08, min(0.92, base))


def attempt_join_template(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    template: Mapping[str, Any],
    rng: random.Random,
    *,
    affinity: Optional[float] = None,
    known_reinvite: bool = False,
) -> Tuple[bool, List[str]]:
    """
    Full join flow: gates → pay hire → consent roll → add member.
    Harder tiers: costlier + lower consent. Soft messages only.
    """
    ensure_party(player)
    notes: List[str] = []
    tid = str(template.get("id") or "")
    # known reinvite: slightly easier affinity floor
    meta = dict((player.get("party_known_meta") or {}).get(tid) or {})
    bond_peak = int(meta.get("bond_peak") or 0)
    if affinity is None:
        # reinvite uses bond; fresh uses soft random
        if known_reinvite:
            affinity = 0.25 + min(0.45, bond_peak * 0.06) + rng.random() * 0.15
        else:
            affinity = 0.2 + rng.random() * 0.45
    aff = float(affinity)

    ok, why = can_recruit_template(player, reg, template, affinity=aff)
    if not ok:
        return False, [why]

    costs = hire_cost_table(template)
    if known_reinvite:
        # known: 40% cheaper
        costs = {k: int(v * 0.6) for k, v in costs.items()}
    afford, why_pay = can_afford_hire(player, costs)
    if not afford:
        return False, [why_pay]

    # pay up-front (commitment)
    if any(int(costs.get(k) or 0) > 0 for k in ("world", "heaven", "hell")):
        notes.append("คุณยื่นของ/ค่าตอบแทนตามที่บรรยากาศบอก...")
        notes.extend(pay_hire(player, costs, fraction=1.0))

    chance = consent_chance(
        template, aff, bond_peak=bond_peak, known=known_reinvite
    )
    if rng.random() > chance:
        # soft fail — keep cost (already paid) as tax for hard tiers
        notes.append("…มันลังเล แล้วถอย — ยังไม่ยอมรับการร่วมทีม")
        notes.append(" (บางอย่างยังไม่พอ — ไม่บอกว่าอะไร)")
        return False, notes

    mem = member_from_template(template, reg, rng)
    msg = add_member(player, mem, reg)
    notes.append(msg)
    if known_reinvite:
        notes.append("  มันจำเส้นทางเก่าได้ — กลับมาร่วมทางอีกครั้ง")
    try:
        from game.domain.equipment import recompute_stats  # may not exist path
    except Exception:
        pass
    return True, notes


def list_known_companions(player: Mapping[str, Any], reg: DataRegistry) -> List[Dict[str, Any]]:
    """UI list for re-invite menu."""
    ensure_party(player)  # type: ignore
    out: List[Dict[str, Any]] = []
    meta = player.get("party_known_meta") or {}
    for mid in player.get("party_known") or []:
        m = dict(meta.get(mid) or {})
        m["id"] = mid
        m["name"] = m.get("name") or mid
        m["kind"] = m.get("kind") or "other"
        m["kind_label"] = kind_label(reg, str(m["kind"]))
        m["in_party"] = _already_in(player, str(mid))
        m["bond_peak"] = int(m.get("bond_peak") or 0)
        out.append(m)
    return out


def reinvite_known_companion(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    companion_id: str,
    rng: random.Random,
) -> Tuple[bool, List[str]]:
    """Re-invite a previously joined companion by id."""
    ensure_party(player)
    cid = str(companion_id)
    if cid not in (player.get("party_known") or []):
        return False, ["…ไม่พบเงาที่คุ้นในความจำ"]
    if _already_in(player, cid):
        return False, ["ร่วมทางอยู่แล้ว"]
    if not _has_slot(player, reg):
        return False, ["ทีมเต็มแล้ว (สูงสุด 3) — ปลดใครก่อน"]
    # player echoes cannot re-pull from template
    if cid.startswith("player:"):
        return False, ["เงาผู้เล่นอื่นต้องพบใหม่ในโลก — เรียกซ้ำจากบัญชีนี้ไม่ได้"]
    tpl = template_by_id(reg, cid)
    if not tpl:
        # fallback meta-only soft block
        return False, ["เงานั้นจางเกินจะเรียกกลับทางนี้"]
    return attempt_join_template(
        player, reg, tpl, rng, known_reinvite=True
    )


def roll_companion_sight(
    player: Mapping[str, Any],
    reg: DataRegistry,
    rng: random.Random,
) -> Optional[Dict[str, Any]]:
    """
    Soft sight entry for a possible companion (P1).
    Does not guarantee recruit success — only discovery.
    """
    if not roll_recruit_sight(player, reg, rng):
        return None
    if not _has_slot(player, reg):
        return None
    offer = try_recruit_template_offer(player, reg, rng)
    if not offer:
        return None
    soft_labels = {
        "spirit": "เงาบางเบา",
        "beast": "ร่างสัตว์เงียบ",
        "heaven_beast": "เงาสว่างปีก",
        "hell_beast": "เงาแดงต่ำ",
        "heaven_god": "รัศมีเลือน",
        "hell_god": "เงาโลหิตนิ่ง",
        "other": "รูปไม่ชัด",
    }
    kind = str(offer.get("kind") or "other")
    return {
        "kind": "companion",
        "label": soft_labels.get(kind, "เงาไม่คุ้น"),
        "hint": rng.choice(
            ["จ้องคุณ", "ไม่หนี", "รออะไรบางอย่าง", "อากาศเปลี่ยนรอบตัว"]
        ),
        "risk": "?",
        "known": False,
        "companion_template_id": offer.get("id"),
        "companion_template": dict(offer),
    }


def soft_party_discovery_lines() -> List[str]:
    """Static soft tips for menus — no formulas."""
    return [
        " สหายไม่ใช่ซื้อจากร้าน — เงาในโลกอาจยอมร่วมทาง",
        " ลองสำรวจ/เข้าหาเมื่อรู้สึกว่าถูกจ้อง… ยื่นมือแล้วรอการยอมรับ",
        " ในทีม: ซุ่มช่วยอัตโน — ยิ่งสัมพันธ์สหายสูง ยิ่งบ่อย (ไม่เสียมานา)",
        " สร้างสัมพันธ์สหาย: ให้ของขวัญ/เงิน (Y) — ชอบอะไรต้องสังเกต",
        " ไม่อยู่ในทีม: bond ลดช้ามาก · เชิญกลับได้จากรายชื่อรู้จัก",
        " สัมพันธ์สหาย ≠ เรโซแนนซ์เรลิก (คอรัส/ภาระเทพ) — คนละชั้น",
        " อ่านสหาย (Y→6): soft ตามชั้นประเมิน — ไม่โชว์ ATK/HP",
    ]


def roll_recruit_sight(player: Mapping[str, Any], reg: DataRegistry, rng: random.Random) -> bool:
    ch = float(_cfg(reg).get("recruit_sight_chance") or 0.12)
    return rng.random() < ch

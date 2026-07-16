"""
Occupation skill trees — prerequisites, multi-currency learn costs, master leases.
Player sees adjacent nodes only; distant nodes stay hidden.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple

from game.data_load.registry import DataRegistry
from game.domain.skill_charges import (
    ensure_skill_charges,
    format_charge_hint,
    is_skill_usable,
    renew_lease,
    set_lease,
)


def ensure_skill_tree_state(player: MutableMapping[str, Any]) -> None:
    player.setdefault("skills", [])
    player.setdefault("base_skills", list(player.get("skills") or []))
    player.setdefault("skill_tree_unlocked", [])
    ensure_skill_charges(player)


def _learn_cfg(skill: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(skill.get("learn") or {})


def skill_requires(skill: Mapping[str, Any]) -> List[str]:
    return [str(x) for x in (skill.get("requires") or [])]


def skill_requires_any(skill: Mapping[str, Any]) -> List[str]:
    return [str(x) for x in (skill.get("requires_any") or [])]


def has_prereqs(player: Mapping[str, Any], skill: Mapping[str, Any]) -> bool:
    owned = set(player.get("skills") or [])
    req = skill_requires(skill)
    if req and not all(r in owned for r in req):
        return False
    any_req = skill_requires_any(skill)
    if any_req and not any(r in owned for r in any_req):
        return False
    return True


def _count_item(player: Mapping[str, Any], item_id: str) -> int:
    ids = list(player.get("inventory_ids") or [])
    return sum(1 for x in ids if x == item_id)


def _remove_items(player: MutableMapping[str, Any], item_id: str, n: int, reg: DataRegistry) -> None:
    ids = list(player.get("inventory_ids") or [])
    left = n
    new_ids: List[str] = []
    for x in ids:
        if x == item_id and left > 0:
            left -= 1
            continue
        new_ids.append(x)
    player["inventory_ids"] = new_ids
    names = [str((reg.items.get(iid) or {}).get("name") or iid) for iid in new_ids]
    if names:
        player["inventory"] = names


def _required_level(sk: Mapping[str, Any], learn: Mapping[str, Any]) -> int:
    if learn.get("require_level") is not None:
        return int(learn["require_level"])
    tier = int(sk.get("tier") or 1)
    return {1: 1, 2: 6, 3: 12, 4: 20, 5: 28}.get(tier, 1)


def check_learn_conditions(
    player: Mapping[str, Any],
    reg: DataRegistry,
    skill_id: str,
) -> Tuple[bool, List[str]]:
    sk = reg.skills.get(skill_id) or {}
    if not sk:
        return False, ["ไม่พบสกิลนี้"]
    if skill_id in (player.get("skills") or []) and is_skill_usable(player, skill_id):
        return False, ["รู้สกิลนี้แล้ว"]

    hints: List[str] = []
    if not has_prereqs(player, sk):
        return False, ["ยังขาดสกิลพื้นฐานที่จำเป็น"]

    learn = _learn_cfg(sk)
    occ = str(player.get("occupation_id") or "")
    tree = str(sk.get("tree") or "")
    allow = [str(x) for x in (learn.get("require_occ") or [])]
    if not allow and tree and tree in (reg.occupations or {}):
        allow = [tree]
    if allow and occ not in allow:
        return False, ["สายอาชีพนี้เรียนสกิลนี้ไม่ได้"]

    need_lv = _required_level(sk, learn)
    if int(player.get("level", 1)) < need_lv:
        hints.append("ระดับการเดินทางยังไม่พอ")

    need_rank = int(learn.get("require_rank_min") or 0)
    if int(player.get("occ_rank_index", 0)) < need_rank:
        hints.append("ตำแหน่งในสายอาชีพยังตื้นเกินไป")

    for qid in learn.get("require_quests") or []:
        if qid not in (player.get("quests_done") or []):
            hints.append("ยังมีเรื่องค้างคาบางอย่าง")
            break

    cw = int(learn.get("cost_world") or 0)
    ch = int(learn.get("cost_heaven") or 0)
    cl = int(learn.get("cost_hell") or 0)
    if int(player.get("money_world", 0)) < cw:
        hints.append("เงินโลกไม่พอ")
    if int(player.get("money_heaven", 0)) < ch:
        hints.append("เงินสวรรค์ไม่พอ")
    if int(player.get("money_hell", 0)) < cl:
        hints.append("เงินนรกไม่พอ")

    for iid, n in (learn.get("cost_items") or {}).items():
        if _count_item(player, str(iid)) < int(n):
            hints.append("ยังขาดวัตถุดิบ/ไอเทมบางอย่าง")
            break

    if hints:
        return False, hints
    return True, []


def learn_skill(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    skill_id: str,
    *,
    free: bool = False,
    from_master: bool = False,
) -> str:
    ensure_skill_tree_state(player)
    sk = reg.skills.get(skill_id) or {}
    if not sk:
        return "ไม่พบสกิล"
    if skill_id in (player.get("skills") or []) and is_skill_usable(player, skill_id):
        return "มีสกิลนี้อยู่แล้ว"

    ok, hints = check_learn_conditions(player, reg, skill_id)
    if not free and not ok:
        return "เรียนไม่ได้: " + " · ".join(hints[:2])

    learn = _learn_cfg(sk)
    if not free:
        cw = int(learn.get("cost_world") or 0)
        chv = int(learn.get("cost_heaven") or 0)
        cl = int(learn.get("cost_hell") or 0)
        player["money_world"] = int(player.get("money_world", 0)) - cw
        player["money_heaven"] = int(player.get("money_heaven", 0)) - chv
        player["money_hell"] = int(player.get("money_hell", 0)) - cl
        for iid, n in (learn.get("cost_items") or {}).items():
            _remove_items(player, str(iid), int(n), reg)

    charge = dict(sk.get("charge") or {})
    mode = str(charge.get("mode") or "none")
    max_uses = charge.get("max_uses")
    if from_master and learn.get("master_id"):
        if mode == "none" and max_uses is None:
            mode = "master_lease"
            max_uses = 10
    name = str(sk.get("name") or skill_id)
    if mode in ("fixed", "master_lease") and max_uses is not None:
        set_lease(
            player,
            skill_id,
            int(max_uses),
            source=str(learn.get("master_id") or "lease"),
        )
        msg = f"เรียนรู้「{name}」· ใช้ได้ {int(max_uses)} ครั้ง"
    else:
        skills = list(player.get("skills") or [])
        if skill_id not in skills:
            skills.append(skill_id)
            player["skills"] = skills
        base = list(player.get("base_skills") or [])
        if skill_id not in base:
            base.append(skill_id)
            player["base_skills"] = base
        msg = f"เรียนรู้「{name}」แล้ว (ถาวร)"

    unlocked = list(player.get("skill_tree_unlocked") or [])
    if skill_id not in unlocked:
        unlocked.append(skill_id)
        player["skill_tree_unlocked"] = unlocked
    # WO-037: Anima soft moment on learn
    try:
        from game.domain.stat_arch import anima_presence_lines

        for ln in anima_presence_lines(player, "learn_skill", reg=reg):
            msg += f"\n{ln}"
    except Exception:
        pass
    # SK-R2: roll skill rank on first learn
    try:
        import random

        from game.domain.skill_rank import apply_learn_rank, ensure_skill_ranks

        ensure_skill_ranks(player)
        if skill_id not in (player.get("skill_ranks") or {}):
            # stable-ish seed from player id + skill for reproducibility in tests if needed
            rng = random.Random(
                hash((str(player.get("id") or ""), skill_id, int(player.get("level") or 1)))
                % (2**31)
            )
            # allow free/master paths to still roll; free may re-call — only if missing
            _rank, notes = apply_learn_rank(player, skill_id, sk, rng, reg)
            for n in notes:
                if n:
                    msg = f"{msg}\n  {n}"
    except Exception:
        pass
    # CM4: soft mind growth on learn (hidden intellect path)
    try:
        from game.domain.combo_mind import note_mind_growth

        mnote = note_mind_growth(
            player, 0.4 if from_master else 0.28, reason="master" if from_master else "learn"
        )
        if mnote:
            msg = f"{msg}\n  {mnote}"
    except Exception:
        pass
    try:
        from game.domain.soft_feel import soft_skill_learn_feel

        feel = soft_skill_learn_feel(sk)
        if feel:
            msg = f"{msg}\n  {feel}"
    except Exception:
        pass
    return msg


def renew_master_skill(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    skill_id: str,
) -> str:
    ensure_skill_tree_state(player)
    sk = reg.skills.get(skill_id) or {}
    if not sk:
        return "ไม่พบสกิล"
    if skill_id not in (player.get("skills") or []):
        return "ยังไม่เคยเรียนสกิลนี้"
    learn = _learn_cfg(sk)
    charge = dict(sk.get("charge") or {})
    uses = int(charge.get("max_uses") or 10)
    rw = learn.get("renew_world")
    rh = learn.get("renew_heaven")
    rl = learn.get("renew_hell")
    if rw is None:
        rw = int(int(learn.get("cost_world") or 0) * 0.6)
    if rh is None:
        rh = int(int(learn.get("cost_heaven") or 0) * 0.6)
    if rl is None:
        rl = int(int(learn.get("cost_hell") or 0) * 0.6)
    rw, rh, rl = int(rw), int(rh), int(rl)
    if (
        int(player.get("money_world", 0)) < rw
        or int(player.get("money_heaven", 0)) < rh
        or int(player.get("money_hell", 0)) < rl
    ):
        return "เงินไม่พอสำหรับเติมครั้งใช้"
    player["money_world"] = int(player.get("money_world", 0)) - rw
    player["money_heaven"] = int(player.get("money_heaven", 0)) - rh
    player["money_hell"] = int(player.get("money_hell", 0)) - rl
    return renew_lease(player, skill_id, uses)


def tree_skills_for_occ(reg: DataRegistry, occupation_id: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sid, sk in (reg.skills or {}).items():
        if sk.get("unit_only"):
            continue
        tree = str(sk.get("tree") or "")
        learn = _learn_cfg(sk)
        occs = [str(x) for x in (learn.get("require_occ") or [])]
        if tree == occupation_id or occupation_id in occs:
            out.append({**sk, "id": sid})
    out.sort(key=lambda s: (int(s.get("tier") or 99), str(s.get("id"))))
    return out


def list_visible_tree_nodes(
    player: Mapping[str, Any],
    reg: DataRegistry,
) -> List[Dict[str, Any]]:
    occ = str(player.get("occupation_id") or "")
    owned = set(player.get("skills") or [])
    nodes = tree_skills_for_occ(reg, occ)

    for sid, sk in (reg.skills or {}).items():
        if sk.get("unit_only"):
            continue
        learn = _learn_cfg(sk)
        methods = list(learn.get("method") or [])
        tree = str(sk.get("tree") or "")
        occs = [str(x) for x in (learn.get("require_occ") or [])]
        if tree or occs:
            continue
        if "self" in methods and int(sk.get("tier") or 0) <= 2:
            if not any(n.get("id") == sid for n in nodes):
                nodes.append({**sk, "id": sid})

    visible: List[Dict[str, Any]] = []
    for sk in nodes:
        sid = str(sk.get("id"))
        if sid in owned:
            status = "owned" if is_skill_usable(player, sid) else "depleted"
        elif has_prereqs(player, sk):
            # only self-learnable via tree UI
            methods = list(_learn_cfg(sk).get("method") or ["self"])
            if "self" in methods or "rank" in methods:
                status = "available"
            else:
                status = "near"  # needs master/quest — show as near
        else:
            req = skill_requires(sk)
            if req and any(r in owned for r in req):
                status = "near"
            else:
                continue
        visible.append({**sk, "id": sid, "_status": status})
    visible.sort(key=lambda s: (int(s.get("tier") or 99), str(s.get("id"))))
    return visible


def format_tree_panel(player: Mapping[str, Any], reg: DataRegistry) -> List[str]:
    ensure_skill_tree_state(player)  # type: ignore[arg-type]
    occ_name = player.get("occupation") or player.get("occupation_id")
    lines = [
        f"── ต้นไม้อาชีพ · {occ_name} ──",
        f" Lv.{player.get('level', 1)} · ตำแหน่ง: {player.get('occ_rank_title') or '-'}",
        (
            f" เงิน โลก {player.get('money_world', 0)} | "
            f"สวรรค์ {player.get('money_heaven', 0)} | "
            f"นรก {player.get('money_hell', 0)}"
        ),
        " (โหนดไกลซ่อน · ต้องมีสกิลพื้นฐานก่อน · ○=เรียนได้ ?=ใกล้)",
    ]
    nodes = list_visible_tree_nodes(player, reg)
    if not nodes:
        lines.append(" ยังไม่เห็นโหนดสกิล — เล่นต่อไป")
        return lines
    for i, sk in enumerate(nodes, 1):
        st = sk.get("_status")
        name = sk.get("name") or sk.get("id")
        tier = sk.get("tier") or "?"
        mp = sk.get("cost_mana")
        mark = {"owned": "✓", "depleted": "×", "available": "○", "near": "?"}.get(str(st), "·")
        extra = ""
        if st == "depleted":
            extra = " (หมดครั้งใช้ — เลือกเพื่อเติม)"
        elif st == "available":
            learn = _learn_cfg(sk)
            bits = []
            if learn.get("cost_world"):
                bits.append(f"โลก{learn['cost_world']}")
            if learn.get("cost_heaven"):
                bits.append(f"สวรรค์{learn['cost_heaven']}")
            if learn.get("cost_hell"):
                bits.append(f"นรก{learn['cost_hell']}")
            if learn.get("cost_items"):
                bits.append("ไอเทม")
            extra = (" | เรียน: " + ",".join(bits)) if bits else " | เรียนได้"
        elif st == "near":
            name = "???"
            extra = " (ใกล้แล้ว — ยังขาดพื้นฐานหรือต้องหาอาจารย์)"
        ch = format_charge_hint(player, str(sk.get("id")), reg) if st in ("owned", "depleted") else ""
        lines.append(f"  {i}. [{mark}] T{tier} {name}{ch}  MP:{mp}{extra}")
    return lines


def get_master(reg: DataRegistry, master_id: str) -> Dict[str, Any]:
    return dict((getattr(reg, "skill_masters", None) or {}).get(master_id) or {})


def list_master_offers(reg: DataRegistry, master_id: str) -> List[Dict[str, Any]]:
    m = get_master(reg, master_id)
    return list(m.get("teaches") or [])


def teach_from_master(
    player: MutableMapping[str, Any],
    reg: DataRegistry,
    master_id: str,
    skill_id: str,
) -> str:
    ensure_skill_tree_state(player)
    offers = list_master_offers(reg, master_id)
    offer = next((o for o in offers if str(o.get("skill_id")) == skill_id), None)
    if not offer:
        return "อาจารย์คนนี้ไม่ได้สอนท่านี้"
    for req in offer.get("require_skills") or []:
        if req not in (player.get("skills") or []):
            return "ยังขาดพื้นฐานที่อาจารย์ต้องการ"
    # renew path if already known but depleted
    if skill_id in (player.get("skills") or []) and not is_skill_usable(player, skill_id):
        fw = int(offer.get("renew_fee_world") if offer.get("renew_fee_world") is not None else int(offer.get("fee_world") or 0) * 0.6)
        fh = int(offer.get("renew_fee_heaven") or 0)
        fl = int(offer.get("renew_fee_hell") or 0)
        if int(player.get("money_world", 0)) < fw:
            return "เงินโลกไม่พอค่าเติม"
        if int(player.get("money_heaven", 0)) < fh:
            return "เงินสวรรค์ไม่พอค่าเติม"
        if int(player.get("money_hell", 0)) < fl:
            return "เงินนรกไม่พอค่าเติม"
        player["money_world"] = int(player.get("money_world", 0)) - fw
        player["money_heaven"] = int(player.get("money_heaven", 0)) - fh
        player["money_hell"] = int(player.get("money_hell", 0)) - fl
        uses = int(offer.get("lease_uses") or 10)
        return renew_lease(player, skill_id, uses)

    fw = int(offer.get("fee_world") or 0)
    fh = int(offer.get("fee_heaven") or 0)
    fl = int(offer.get("fee_hell") or 0)
    if int(player.get("money_world", 0)) < fw:
        return "เงินโลกไม่พอค่าเรียน"
    if int(player.get("money_heaven", 0)) < fh:
        return "เงินสวรรค์ไม่พอค่าเรียน"
    if int(player.get("money_hell", 0)) < fl:
        return "เงินนรกไม่พอค่าเรียน"
    player["money_world"] = int(player.get("money_world", 0)) - fw
    player["money_heaven"] = int(player.get("money_heaven", 0)) - fh
    player["money_hell"] = int(player.get("money_hell", 0)) - fl
    uses = offer.get("lease_uses")
    sk = reg.skills.get(skill_id) or {}
    name = str(sk.get("name") or skill_id)
    if uses is not None:
        set_lease(player, skill_id, int(uses), source=master_id)
        return f"อาจารย์ถ่ายทอด「{name}」· ใช้ได้ {int(uses)} ครั้ง"
    skills = list(player.get("skills") or [])
    if skill_id not in skills:
        skills.append(skill_id)
        player["skills"] = skills
    return f"อาจารย์ถ่ายทอด「{name}」อย่างถาวร"


def pick_random_master_id(reg: DataRegistry, rng: Any) -> Optional[str]:
    masters = getattr(reg, "skill_masters", None) or {}
    if not masters:
        return None
    ids = list(masters.keys())
    return str(rng.choice(ids))

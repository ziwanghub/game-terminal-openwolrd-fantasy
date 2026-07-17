"""
WO-Storage-1.2 — Shared team vault (คลังทีม / แชร์ user+pass).

- Bag (40) = combat loadout on each character
- Vault (200) = shared stash: equipment, healing, mat, money (same world)
- Any player who knows vault user + pass can open the same vault file
- Files: saves/{world_id}/vaults/*.json  (not inside one player save)
- Auto stash: optional; needs session unlock; mat/other/healing/food
"""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

# Fallback if YAML missing
DEFAULT_CAP = 200
MONEY_KEYS = ("world", "heaven", "hell")
MONEY_PLAYER_FIELD = {
    "world": "money_world",
    "heaven": "money_heaven",
    "hell": "money_hell",
}
MONEY_LABEL = {
    "world": "โลก",
    "heaven": "สวรรค์",
    "hell": "นรก",
}


def _cfg() -> Dict[str, Any]:
    try:
        from game.config import DATA_DIR
        import yaml

        path = Path(DATA_DIR) / "meta" / "warehouse.yaml"
        if path.is_file():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(raw, dict):
                return raw
    except Exception:
        pass
    return {
        "enabled": True,
        "shared": True,
        "default_cap": DEFAULT_CAP,
        "auto_stash_default": False,
        "auto_stash_categories": ["material", "other", "healing", "food"],
        "auto_stash_block_categories": [
            "equipment",
            "chest",
            "card",
            "relic",
        ],
    }


def default_cap() -> int:
    return max(1, int(_cfg().get("default_cap") or DEFAULT_CAP))


def _world_id(player: Mapping[str, Any]) -> str:
    return str(player.get("world_id") or "default")


def _user_slug(user: str) -> str:
    u = str(user or "").strip()
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in u)
    safe = safe.strip("_")[:48] or "vault"
    # disambiguate unicode-heavy names
    h = hashlib.sha256(u.encode("utf-8")).hexdigest()[:8]
    return f"{safe}__{h}"


def vaults_dir(world_id: str) -> Path:
    from game.config import SAVES_DIR

    d = Path(SAVES_DIR) / str(world_id or "default") / "vaults"
    d.mkdir(parents=True, exist_ok=True)
    return d


def vault_path(world_id: str, user: str) -> Path:
    return vaults_dir(world_id) / f"{_user_slug(user)}.json"


def _empty_items() -> Dict[str, Any]:
    return {
        "inventory_ids": [],
        "inventory_qty": [],
        "inventory_rarities": [],
        "inventory": [],
        "inventory_items": [],
    }


def _normalize_items(items: Any) -> Dict[str, Any]:
    if not isinstance(items, dict):
        items = {}
    out = _empty_items()
    ids = list(items.get("inventory_ids") or [])
    qtys = list(items.get("inventory_qty") or [])
    rares = list(items.get("inventory_rarities") or [])
    inv = list(items.get("inventory") or [])
    while len(qtys) < len(ids):
        qtys.append(1)
    while len(rares) < len(ids):
        rares.append("common")
    while len(inv) < len(ids):
        inv.append("")
    out["inventory_ids"] = [str(x) for x in ids]
    out["inventory_qty"] = [max(1, int(q or 1)) for q in qtys[: len(ids)]]
    out["inventory_rarities"] = [str(r or "common") for r in rares[: len(ids)]]
    out["inventory"] = [str(x) for x in inv[: len(ids)]]
    insts = list(items.get("inventory_items") or [])
    if insts and len(insts) == len(ids):
        out["inventory_items"] = insts
    else:
        out["inventory_items"] = []
    return out


def _normalize_money(money: Any) -> Dict[str, int]:
    if not isinstance(money, dict):
        money = {}
    return {k: max(0, int(money.get(k) or 0)) for k in MONEY_KEYS}


def _new_vault_blob(user: str, password: str, *, created_by: str = "") -> Dict[str, Any]:
    salt = secrets.token_hex(16)
    return {
        "schema": 2,
        "shared": True,
        "user": str(user).strip(),
        "pass_salt": salt,
        "pass_hash": _hash_pass(salt, password),
        "cap": default_cap(),
        "items": _empty_items(),
        "money": {k: 0 for k in MONEY_KEYS},
        "created_by": str(created_by or ""),
        "members_note": "ใครรู้ user+pass ใช้คลังนี้ร่วมกันได้ (โลกเดียวกัน)",
    }


def load_vault_file(world_id: str, user: str) -> Optional[Dict[str, Any]]:
    path = vault_path(world_id, user)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        raw["user"] = str(raw.get("user") or user)
        raw["items"] = _normalize_items(raw.get("items"))
        raw["money"] = _normalize_money(raw.get("money"))
        raw["cap"] = max(1, int(raw.get("cap") or default_cap()))
        return raw
    except Exception:
        return None


def save_vault_file(world_id: str, vault: Mapping[str, Any]) -> bool:
    user = str(vault.get("user") or "").strip()
    if not user:
        return False
    path = vault_path(world_id, user)
    payload = {
        "schema": 2,
        "shared": True,
        "user": user,
        "pass_salt": str(vault.get("pass_salt") or ""),
        "pass_hash": str(vault.get("pass_hash") or ""),
        "cap": max(1, int(vault.get("cap") or default_cap())),
        "items": _normalize_items(vault.get("items")),
        "money": _normalize_money(vault.get("money")),
        "created_by": str(vault.get("created_by") or ""),
        "members_note": str(
            vault.get("members_note")
            or "ใครรู้ user+pass ใช้คลังนี้ร่วมกันได้ (โลกเดียวกัน)"
        ),
    }
    try:
        from game.domain.file_lock import world_file_lock

        with world_file_lock(world_id, f"vault_{_user_slug(user)}", timeout=6.0):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return True
    except Exception:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return True
        except Exception:
            return False


def vault_exists(world_id: str, user: str) -> bool:
    return vault_path(world_id, user).is_file()


def ensure_warehouse(player: MutableMapping[str, Any]) -> Dict[str, Any]:
    """
    Player-side session mirror + prefs.
    Shared vault body lives in vault file; mirrored into player['warehouse'] when unlocked.
    Migrates legacy personal warehouse (schema 1 with pass_hash on player) → vault file once.
    """
    w = player.get("warehouse")
    if not isinstance(w, dict):
        w = {}
    w.setdefault("schema", 2)
    w["schema"] = max(2, int(w.get("schema") or 2))
    w.setdefault("shared", True)
    w["shared"] = True
    w.setdefault("cap", default_cap())
    w["cap"] = max(1, int(w.get("cap") or default_cap()))
    w.setdefault("user", "")
    w.setdefault("last_user", str(w.get("user") or w.get("last_user") or ""))
    # strip personal pass from player after migrate (secrets only on vault file)
    prefs = w.get("prefs")
    if not isinstance(prefs, dict):
        prefs = {}
    cfg = _cfg()
    prefs.setdefault("auto_stash", bool(cfg.get("auto_stash_default", False)))
    cats = prefs.get("auto_stash_categories")
    if not isinstance(cats, list) or not cats:
        prefs["auto_stash_categories"] = list(
            cfg.get("auto_stash_categories")
            or ["material", "other", "healing", "food"]
        )
    w["prefs"] = prefs
    w["items"] = _normalize_items(w.get("items"))
    w["money"] = _normalize_money(w.get("money"))
    # one-time migrate personal → shared vault file
    if w.get("pass_hash") and w.get("pass_salt") and w.get("user"):
        wid = _world_id(player)
        uname = str(w.get("user"))
        if not vault_exists(wid, uname):
            blob = {
                "schema": 2,
                "shared": True,
                "user": uname,
                "pass_salt": w.get("pass_salt"),
                "pass_hash": w.get("pass_hash"),
                "cap": w.get("cap") or default_cap(),
                "items": _normalize_items(w.get("items")),
                "money": _normalize_money(w.get("money")),
                "created_by": str(player.get("id") or player.get("name") or ""),
            }
            save_vault_file(wid, blob)
        w["last_user"] = uname
        # clear secrets + stash from player save (vault file is source of truth)
        w.pop("pass_hash", None)
        w.pop("pass_salt", None)
        w.pop("pass_plain", None)
        if not is_unlocked(player):
            w["items"] = _empty_items()
            w["money"] = {k: 0 for k in MONEY_KEYS}
    player["warehouse"] = w
    return w


def is_setup(player: Mapping[str, Any]) -> bool:
    """True if this session has an open shared vault (or legacy unlocked)."""
    return is_unlocked(player) and bool(
        (player.get("warehouse") or {}).get("user")
        or player.get("_vault_user")
    )


def is_unlocked(player: Mapping[str, Any]) -> bool:
    return bool(player.get("_warehouse_unlocked"))


def lock_session(player: MutableMapping[str, Any]) -> None:
    """Flush vault then clear session (call on PERSONAL exit / character switch)."""
    if is_unlocked(player):
        persist_active_vault(player)
    player.pop("_warehouse_unlocked", None)
    player.pop("_vault_user", None)
    # clear live stash from player memory (file keeps data)
    w = player.get("warehouse")
    if isinstance(w, dict):
        last = str(w.get("user") or w.get("last_user") or "")
        w["last_user"] = last
        w["user"] = last
        w["items"] = _empty_items()
        w["money"] = {k: 0 for k in MONEY_KEYS}
        w.pop("pass_hash", None)
        w.pop("pass_salt", None)
        player["warehouse"] = w


def unlock_session(player: MutableMapping[str, Any], *, vault_user: str = "") -> None:
    player["_warehouse_unlocked"] = True
    if vault_user:
        player["_vault_user"] = str(vault_user)


def default_user(player: Mapping[str, Any]) -> str:
    w = player.get("warehouse") or {}
    last = str(w.get("last_user") or w.get("user") or "").strip()
    if last:
        return last
    return str(player.get("name") or player.get("id") or "ทีม").strip() or "ทีม"


def _hash_pass(salt: str, password: str) -> str:
    raw = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _apply_vault_to_player(player: MutableMapping[str, Any], vault: Mapping[str, Any]) -> None:
    ensure_warehouse(player)
    w = player["warehouse"]
    w["user"] = str(vault.get("user") or "")
    w["last_user"] = w["user"]
    w["cap"] = max(1, int(vault.get("cap") or default_cap()))
    w["items"] = _normalize_items(vault.get("items"))
    w["money"] = _normalize_money(vault.get("money"))
    # never keep pass on player
    w.pop("pass_hash", None)
    w.pop("pass_salt", None)
    player["warehouse"] = w
    unlock_session(player, vault_user=w["user"])


def persist_active_vault(player: MutableMapping[str, Any]) -> bool:
    """Write session warehouse body back to shared vault file."""
    if not is_unlocked(player):
        return False
    ensure_warehouse(player)
    w = player["warehouse"]
    user = str(w.get("user") or player.get("_vault_user") or "").strip()
    if not user:
        return False
    wid = _world_id(player)
    disk = load_vault_file(wid, user)
    if not disk:
        return False
    disk["items"] = _normalize_items(w.get("items"))
    disk["money"] = _normalize_money(w.get("money"))
    disk["cap"] = max(1, int(w.get("cap") or disk.get("cap") or default_cap()))
    return save_vault_file(wid, disk)


def register(
    player: MutableMapping[str, Any],
    password: str,
    *,
    user: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Create a new shared vault (user + pass) for this world.
    Fails if vault user already exists — use login instead.
    """
    ensure_warehouse(player)
    uname = str(user or "").strip() or default_user(player)
    pw = str(password or "")
    if len(pw) < 1:
        return False, "ตั้งรหัสผ่านอย่างน้อย 1 ตัวอักษร"
    wid = _world_id(player)
    if vault_exists(wid, uname):
        return False, f"คลัง 「{uname}」 มีแล้ว — ใส่รหัสผ่านเพื่อเข้า (แชร์ทีม)"
    blob = _new_vault_blob(
        uname,
        pw,
        created_by=str(player.get("id") or player.get("name") or ""),
    )
    if not save_vault_file(wid, blob):
        return False, "สร้างไฟล์คลังไม่สำเร็จ"
    _apply_vault_to_player(player, blob)
    return True, f"สร้างคลังทีม 「{uname}」 แล้ว · แชร์ user+pass กับเพื่อนได้"


def login(
    player: MutableMapping[str, Any],
    password: str,
    *,
    user: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Open shared vault by user + pass (any character in the same world).
    """
    ensure_warehouse(player)
    uname = str(user or "").strip() or default_user(player)
    wid = _world_id(player)
    vault = load_vault_file(wid, uname)
    if not vault:
        return False, f"ไม่พบคลัง 「{uname}」 — สร้างใหม่หรือตรวจชื่อ"
    salt = str(vault.get("pass_salt") or "")
    expect = str(vault.get("pass_hash") or "")
    if not salt or not expect:
        return False, "คลังเสียหาย"
    if _hash_pass(salt, str(password or "")) != expect:
        return False, "รหัสผ่านไม่ถูกต้อง"
    _apply_vault_to_player(player, vault)
    return True, f"เข้าคลังทีม 「{uname}」 แล้ว · แชร์ของกับคนที่รู้รหัส"


def require_unlocked(player: Mapping[str, Any]) -> Tuple[bool, str]:
    if not is_unlocked(player):
        return False, "ยังไม่เข้าคลัง — ใส่ user + รหัสผ่านก่อน"
    if not (player.get("warehouse") or {}).get("user") and not player.get("_vault_user"):
        return False, "ยังไม่ผูกคลังทีม"
    return True, ""


def slots_used(player: Mapping[str, Any]) -> int:
    ensure_warehouse(player)  # type: ignore[arg-type]
    items = (player.get("warehouse") or {}).get("items") or {}
    return len(list(items.get("inventory_ids") or []))


def slots_cap(player: Mapping[str, Any]) -> int:
    ensure_warehouse(player)  # type: ignore[arg-type]
    return max(1, int((player.get("warehouse") or {}).get("cap") or default_cap()))


def slots_free(player: Mapping[str, Any]) -> int:
    return max(0, slots_cap(player) - slots_used(player))


def money_held(player: Mapping[str, Any], key: str) -> int:
    field = MONEY_PLAYER_FIELD.get(key, f"money_{key}")
    return max(0, int(player.get(field) or 0))


def money_stored(player: Mapping[str, Any], key: str) -> int:
    ensure_warehouse(player)  # type: ignore[arg-type]
    m = (player.get("warehouse") or {}).get("money") or {}
    return max(0, int(m.get(key) or 0))


def deposit_money(
    player: MutableMapping[str, Any],
    key: str,
    amount: int,
) -> Tuple[bool, str]:
    ok, msg = require_unlocked(player)
    if not ok:
        return False, msg
    k = str(key or "").lower().replace("money_", "")
    if k not in MONEY_KEYS:
        return False, "สกุลเงินไม่รู้จัก (world/heaven/hell)"
    n = int(amount or 0)
    if n <= 0:
        return False, "จำนวนต้องมากกว่า 0"
    ensure_warehouse(player)
    field = MONEY_PLAYER_FIELD[k]
    have = money_held(player, k)
    if have < n:
        return False, f"เงิน{MONEY_LABEL[k]}ไม่พอ (มี {have})"
    player[field] = have - n
    w = player["warehouse"]
    w["money"][k] = money_stored(player, k) + n
    player["warehouse"] = w
    persist_active_vault(player)
    return True, f"ฝาก {MONEY_LABEL[k]} {n} → คลัง (ฝากรวม {w['money'][k]})"


def withdraw_money(
    player: MutableMapping[str, Any],
    key: str,
    amount: int,
) -> Tuple[bool, str]:
    ok, msg = require_unlocked(player)
    if not ok:
        return False, msg
    k = str(key or "").lower().replace("money_", "")
    if k not in MONEY_KEYS:
        return False, "สกุลเงินไม่รู้จัก (world/heaven/hell)"
    n = int(amount or 0)
    if n <= 0:
        return False, "จำนวนต้องมากกว่า 0"
    ensure_warehouse(player)
    stored = money_stored(player, k)
    if stored < n:
        return False, f"ในคลังมีเงิน{MONEY_LABEL[k]}ไม่พอ (มี {stored})"
    field = MONEY_PLAYER_FIELD[k]
    w = player["warehouse"]
    w["money"][k] = stored - n
    player[field] = money_held(player, k) + n
    player["warehouse"] = w
    persist_active_vault(player)
    return True, f"ถอน {MONEY_LABEL[k]} {n} → ถือ (เหลือในคลัง {w['money'][k]})"


def _wh_find_stack(items: Mapping[str, Any], item_id: str, rarity: str) -> int:
    ids = list(items.get("inventory_ids") or [])
    rares = list(items.get("inventory_rarities") or [])
    rid = str(rarity or "common")
    for i, iid in enumerate(ids):
        if str(iid) != str(item_id):
            continue
        r = str(rares[i] if i < len(rares) else "common") or "common"
        if r == rid:
            return i
    return -1


def _wh_qty_at(items: Mapping[str, Any], index: int) -> int:
    ids = list(items.get("inventory_ids") or [])
    if index < 0 or index >= len(ids):
        return 0
    qtys = list(items.get("inventory_qty") or [])
    if index < len(qtys):
        return max(1, int(qtys[index] or 1))
    return 1


def _wh_can_accept(
    player: Mapping[str, Any],
    item_id: str,
    rarity: str,
    reg: Any,
    *,
    amount: int = 1,
) -> bool:
    from game.domain.bag_stack import is_stackable_item

    ensure_warehouse(player)  # type: ignore[arg-type]
    items = (player.get("warehouse") or {}).get("items") or {}
    if is_stackable_item(item_id, reg):
        if _wh_find_stack(items, item_id, rarity) >= 0:
            return True
    return slots_free(player) > 0


def _wh_add(
    player: MutableMapping[str, Any],
    item_id: str,
    rarity: str,
    qty: int,
    reg: Any,
    *,
    display: str = "",
    inst: Optional[Dict[str, Any]] = None,
) -> bool:
    """Add units into warehouse (stack or new slot)."""
    from game.domain.bag_stack import is_stackable_item

    ensure_warehouse(player)
    w = player["warehouse"]
    items = w["items"]
    rid = str(rarity or "common")
    n = max(1, int(qty))
    shown = display or str(item_id)

    if is_stackable_item(item_id, reg):
        idx = _wh_find_stack(items, item_id, rid)
        if idx >= 0:
            qtys = list(items["inventory_qty"])
            qtys[idx] = _wh_qty_at(items, idx) + n
            items["inventory_qty"] = qtys
            insts = list(items.get("inventory_items") or [])
            if idx < len(insts) and isinstance(insts[idx], dict):
                insts[idx]["qty"] = qtys[idx]
                items["inventory_items"] = insts
            w["items"] = items
            player["warehouse"] = w
            return True
        if slots_free(player) <= 0:
            return False
        items["inventory_ids"] = list(items["inventory_ids"]) + [str(item_id)]
        items["inventory_rarities"] = list(items["inventory_rarities"]) + [rid]
        items["inventory_qty"] = list(items["inventory_qty"]) + [n]
        items["inventory"] = list(items["inventory"]) + [shown]
        insts = list(items.get("inventory_items") or [])
        if insts and len(insts) == len(items["inventory_ids"]) - 1:
            row = dict(inst) if isinstance(inst, dict) else {"id": item_id, "rarity": rid}
            row["qty"] = n
            row["location"] = "warehouse"
            insts.append(row)
            items["inventory_items"] = insts
        elif not insts:
            items["inventory_items"] = []
        w["items"] = items
        player["warehouse"] = w
        return True

    # non-stackable: one slot per unit
    for _ in range(n):
        if slots_free(player) <= 0:
            return False
        items = w["items"]
        items["inventory_ids"] = list(items["inventory_ids"]) + [str(item_id)]
        items["inventory_rarities"] = list(items["inventory_rarities"]) + [rid]
        items["inventory_qty"] = list(items["inventory_qty"]) + [1]
        items["inventory"] = list(items["inventory"]) + [shown]
        insts = list(items.get("inventory_items") or [])
        if insts and len(insts) == len(items["inventory_ids"]) - 1:
            row = dict(inst) if isinstance(inst, dict) else {"id": item_id, "rarity": rid}
            row["qty"] = 1
            row["location"] = "warehouse"
            insts.append(row)
            items["inventory_items"] = insts
        w["items"] = items
        player["warehouse"] = w
    return True


def _wh_take_slot(
    player: MutableMapping[str, Any],
    index: int,
    qty: int,
) -> Optional[Tuple[str, str, int, str, Optional[Dict[str, Any]]]]:
    """
    Remove qty from warehouse slot.
    Returns (item_id, rarity, qty_taken, display, inst_or_none) or None.
    """
    ensure_warehouse(player)
    w = player["warehouse"]
    items = w["items"]
    ids = list(items.get("inventory_ids") or [])
    if index < 0 or index >= len(ids):
        return None
    have = _wh_qty_at(items, index)
    n = max(1, min(int(qty), have))
    iid = str(ids[index])
    rares = list(items.get("inventory_rarities") or [])
    rid = str(rares[index] if index < len(rares) else "common") or "common"
    inv = list(items.get("inventory") or [])
    shown = str(inv[index] if index < len(inv) else iid)
    insts = list(items.get("inventory_items") or [])
    inst = dict(insts[index]) if index < len(insts) and isinstance(insts[index], dict) else None

    qtys = list(items.get("inventory_qty") or [])
    if have - n >= 1:
        qtys[index] = have - n
        items["inventory_qty"] = qtys
        if inst and index < len(insts):
            insts[index]["qty"] = qtys[index]
            items["inventory_items"] = insts
        w["items"] = items
        player["warehouse"] = w
        return iid, rid, n, shown, dict(inst) if inst else None

    # remove whole slot
    ids.pop(index)
    if index < len(rares):
        rares.pop(index)
    if index < len(qtys):
        qtys.pop(index)
    if index < len(inv):
        inv.pop(index)
    if index < len(insts):
        insts.pop(index)
    items["inventory_ids"] = ids
    items["inventory_rarities"] = rares[: len(ids)]
    items["inventory_qty"] = qtys[: len(ids)]
    items["inventory"] = inv[: len(ids)]
    if insts:
        items["inventory_items"] = insts[: len(ids)]
    else:
        items["inventory_items"] = []
    w["items"] = items
    player["warehouse"] = w
    return iid, rid, n, shown, inst


def deposit_item_at(
    player: MutableMapping[str, Any],
    bag_index: int,
    reg: Any,
    *,
    qty: int = 1,
) -> Tuple[bool, str]:
    """Move item units from bag slot → warehouse (atomic)."""
    ok, msg = require_unlocked(player)
    if not ok:
        return False, msg
    from game.domain.bag_stack import ensure_inventory_qty, qty_at
    from game.domain.equipment import item_by_id
    from game.domain.rarity import remove_inventory_at_index

    ensure_inventory_qty(player)
    ids = list(player.get("inventory_ids") or [])
    if bag_index < 0 or bag_index >= len(ids):
        return False, "ไม่มีช่องนั้นในกระเป๋า"
    iid = str(ids[bag_index])
    rares = list(player.get("inventory_rarities") or [])
    rid = str(rares[bag_index] if bag_index < len(rares) else "common") or "common"
    have = qty_at(player, bag_index)
    n = max(1, min(int(qty or 1), have))
    it = item_by_id(reg, iid) or {}
    try:
        from game.domain.rarity import display_item_name

        shown = display_item_name(str(it.get("name") or iid), rid, reg)
    except Exception:
        shown = str(it.get("name") or iid)

    if not _wh_can_accept(player, iid, rid, reg, amount=n):
        return False, f"คลังเต็ม ({slots_used(player)}/{slots_cap(player)})"

    # snapshot for rollback
    bag_snap = {
        "inventory_ids": list(player.get("inventory_ids") or []),
        "inventory_qty": list(player.get("inventory_qty") or []),
        "inventory_rarities": list(player.get("inventory_rarities") or []),
        "inventory": list(player.get("inventory") or []),
        "inventory_items": list(player.get("inventory_items") or []),
    }
    ensure_warehouse(player)
    wh_snap = {
        "items": {
            k: list(v) if isinstance(v, list) else v
            for k, v in ((player["warehouse"].get("items") or {}).items())
        }
    }

    # remove from bag
    inst_out: Optional[Dict[str, Any]] = None
    try:
        insts = list(player.get("inventory_items") or [])
        if bag_index < len(insts) and isinstance(insts[bag_index], dict):
            inst_out = dict(insts[bag_index])
        if n >= have:
            removed = remove_inventory_at_index(player, bag_index, reg)
            if not removed:
                return False, "ย้ายจากกระเป๋าไม่สำเร็จ"
        else:
            from game.domain.bag_stack import set_qty_at

            set_qty_at(player, bag_index, have - n)
            if inst_out is not None and bag_index < len(insts):
                insts[bag_index]["qty"] = have - n
                player["inventory_items"] = insts
        if not _wh_add(player, iid, rid, n, reg, display=shown, inst=inst_out):
            # rollback bag
            for k, v in bag_snap.items():
                player[k] = v
            return False, "คลังรับของไม่ได้ — คืนกระเป๋าแล้ว"
    except Exception as e:
        for k, v in bag_snap.items():
            player[k] = v
        if "items" in wh_snap:
            player["warehouse"]["items"] = wh_snap["items"]
        return False, f"ย้ายล้มเหลว ({e})"

    persist_active_vault(player)
    return True, f"ฝาก 「{shown}」 ×{n} เข้าคลังทีม"


def withdraw_item_at(
    player: MutableMapping[str, Any],
    wh_index: int,
    reg: Any,
    *,
    qty: int = 1,
) -> Tuple[bool, str]:
    """Move item units from warehouse → bag (atomic)."""
    ok, msg = require_unlocked(player)
    if not ok:
        return False, msg
    from game.domain.equipment import add_item

    ensure_warehouse(player)
    items = player["warehouse"]["items"]
    ids = list(items.get("inventory_ids") or [])
    if wh_index < 0 or wh_index >= len(ids):
        return False, "ไม่มีช่องนั้นในคลัง"
    have = _wh_qty_at(items, wh_index)
    n = max(1, min(int(qty or 1), have))

    # capacity check for bag (stack may not need slot)
    iid = str(ids[wh_index])
    rares = list(items.get("inventory_rarities") or [])
    rid = str(rares[wh_index] if wh_index < len(rares) else "common") or "common"
    from game.domain.bag_stack import can_accept_item

    if not can_accept_item(player, iid, reg, rarity=rid, amount=n):
        return False, "กระเป๋าเต็ม — ถอนไม่ได้"

    taken = _wh_take_slot(player, wh_index, n)
    if not taken:
        return False, "ถอนจากคลังไม่สำเร็จ"
    tid, trid, tn, shown, _inst = taken
    result = add_item(player, tid, reg, rarity=trid, amount=tn)
    if not result:
        # rollback into warehouse
        _wh_add(player, tid, trid, tn, reg, display=shown, inst=_inst)
        persist_active_vault(player)
        return False, "กระเป๋ารับของไม่ได้ — คืนคลังแล้ว"
    persist_active_vault(player)
    return True, f"ถอน 「{shown}」 ×{tn} เข้ากระเป๋า"


# ── WO-Storage-1.1: bulk parse + batch transfer ───────────────────────


def parse_slot_spec(
    raw: str,
    *,
    max_index_1based: int,
) -> Tuple[Optional[List[int]], str]:
    """
    Parse deposit slot picks (1-based display numbers).

    Examples: "2" | "2 5 7" | "2-5" | "2-4 7"
    Returns (0-based unique indices sorted ascending, error_msg).
    Empty / 0 / q → (None, "cancel").
    """
    s = str(raw or "").strip().lower()
    if not s or s in ("0", "q", "cancel", "ยกเลิก"):
        return None, "cancel"
    if s in ("a", "all", "junk", "mat"):
        return None, "auto_mat"  # caller expands
    out: List[int] = []
    for tok in s.replace(",", " ").split():
        tok = tok.strip()
        if not tok:
            continue
        if "-" in tok and not tok.startswith("-"):
            parts = tok.split("-", 1)
            try:
                a, b = int(parts[0]), int(parts[1])
            except Exception:
                return None, f"ช่วงไม่ถูกต้อง: {tok}"
            if a > b:
                a, b = b, a
            for n in range(a, b + 1):
                if 1 <= n <= max_index_1based:
                    out.append(n - 1)
        else:
            try:
                n = int(tok)
            except Exception:
                return None, f"เลขไม่ถูกต้อง: {tok}"
            if 1 <= n <= max_index_1based:
                out.append(n - 1)
            else:
                return None, f"ไม่มีช่อง {n}"
    if not out:
        return None, "ไม่ได้เลือกช่อง"
    # unique keep order then sort asc for stable display; apply reverse later
    seen = set()
    uniq: List[int] = []
    for i in out:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    uniq.sort()
    return uniq, ""


def parse_withdraw_spec(
    raw: str,
    *,
    max_index_1based: int,
) -> Tuple[Optional[List[Tuple[int, Optional[int]]]], str]:
    """
    Parse withdraw picks.

    "3"       → slot 3, full stack (qty=None)
    "1:4"     → slot 1 qty 4
    "1:4 2:1" → multi
    "2-3"     → slots 2–3 full stacks
    Returns list of (0-based index, qty_or_None), error.
    """
    s = str(raw or "").strip().lower()
    if not s or s in ("0", "q", "cancel", "ยกเลิก"):
        return None, "cancel"
    out: List[Tuple[int, Optional[int]]] = []
    for tok in s.replace(",", " ").split():
        tok = tok.strip()
        if not tok:
            continue
        if ":" in tok:
            left, right = tok.split(":", 1)
            try:
                n = int(left)
                q = int(right)
            except Exception:
                return None, f"รูปแบบ n:qty ไม่ถูก: {tok}"
            if not (1 <= n <= max_index_1based):
                return None, f"ไม่มีช่อง {n}"
            if q < 1:
                return None, f"จำนวนต้อง ≥1: {tok}"
            out.append((n - 1, q))
        elif "-" in tok and not tok.startswith("-"):
            parts = tok.split("-", 1)
            try:
                a, b = int(parts[0]), int(parts[1])
            except Exception:
                return None, f"ช่วงไม่ถูกต้อง: {tok}"
            if a > b:
                a, b = b, a
            for n in range(a, b + 1):
                if 1 <= n <= max_index_1based:
                    out.append((n - 1, None))
                else:
                    return None, f"ไม่มีช่อง {n}"
        else:
            try:
                n = int(tok)
            except Exception:
                return None, f"เลขไม่ถูกต้อง: {tok}"
            if not (1 <= n <= max_index_1based):
                return None, f"ไม่มีช่อง {n}"
            out.append((n - 1, None))
    if not out:
        return None, "ไม่ได้เลือกช่อง"
    # de-dupe by index: later token wins qty
    by_i: Dict[int, Optional[int]] = {}
    for i, q in out:
        by_i[i] = q
    merged = sorted(by_i.items(), key=lambda x: x[0])
    return [(i, q) for i, q in merged], ""


def bag_mat_junk_indices(player: Mapping[str, Any], reg: Any) -> List[int]:
    """0-based bag indices eligible for `a` / Auto (mat/junk/healing/food)."""
    ids = list(player.get("inventory_ids") or [])
    out: List[int] = []
    for i, iid in enumerate(ids):
        if can_auto_stash_item(str(iid), reg, player):
            out.append(i)
    return out


def deposit_items_batch(
    player: MutableMapping[str, Any],
    reg: Any,
    indices_0: Sequence[int],
    *,
    full_stack: bool = True,
) -> Tuple[List[str], List[str]]:
    """
    Deposit multiple bag slots (full stack each).
    Apply high index first so removals do not shift lower indices.
    Returns (success_lines, skip_lines).
    """
    from game.domain.bag_stack import qty_at

    ok_lines: List[str] = []
    skip: List[str] = []
    # unique + reverse
    seen = set()
    ordered: List[int] = []
    for i in sorted(set(int(x) for x in indices_0), reverse=True):
        if i in seen:
            continue
        seen.add(i)
        ordered.append(i)
    for idx in ordered:
        ids = list(player.get("inventory_ids") or [])
        if idx < 0 or idx >= len(ids):
            skip.append(f"ช่อง {idx + 1} ไม่มี")
            continue
        q = qty_at(player, idx) if full_stack else 1
        ok, msg = deposit_item_at(player, idx, reg, qty=q)
        if ok:
            # strip leading verb for bullet
            soft = msg
            if soft.startswith("ฝาก "):
                soft = soft[3:]
            if " เข้าคลัง" in soft:
                soft = soft.split(" เข้าคลัง")[0]
            ok_lines.append(soft.strip())
        else:
            skip.append(f"ช่อง {idx + 1}: {msg}")
    return ok_lines, skip


def withdraw_items_batch(
    player: MutableMapping[str, Any],
    reg: Any,
    picks: Sequence[Tuple[int, Optional[int]]],
) -> Tuple[List[str], List[str]]:
    """
    Withdraw multiple warehouse slots.
    picks: (0-based index, qty_or_None=full). High index first.
    """
    ok_lines: List[str] = []
    skip: List[str] = []
    # sort reverse by index
    ordered = sorted(list(picks), key=lambda x: x[0], reverse=True)
    for idx, qty in ordered:
        ensure_warehouse(player)
        items = player["warehouse"]["items"]
        ids = list(items.get("inventory_ids") or [])
        if idx < 0 or idx >= len(ids):
            skip.append(f"ช่อง {idx + 1} ไม่มี")
            continue
        have = _wh_qty_at(items, idx)
        n = have if qty is None else max(1, min(int(qty), have))
        ok, msg = withdraw_item_at(player, idx, reg, qty=n)
        if ok:
            soft = msg
            if soft.startswith("ถอน "):
                soft = soft[3:]
            if " เข้ากระเป๋า" in soft:
                soft = soft.split(" เข้ากระเป๋า")[0]
            ok_lines.append(soft.strip())
        else:
            skip.append(f"ช่อง {idx + 1}: {msg}")
    return ok_lines, skip


def format_warehouse_status_lines(player: Mapping[str, Any]) -> List[str]:
    ensure_warehouse(player)  # type: ignore[arg-type]
    w = player.get("warehouse") or {}
    used, cap = slots_used(player), slots_cap(player)
    uname = str(w.get("user") or default_user(player))
    # compact header: คลังทีม · Name · 12/200
    lines = [
        f" คลังทีม · {uname} · {used}/{cap}",
        "---",
        "  แชร์: ใครรู้ user+pass (โลกนี้) เข้าคลังเดียวกันได้",
        f" เงินฝาก  โลก {money_stored(player, 'world')}  ·  "
        f"สวรรค์ {money_stored(player, 'heaven')}  ·  "
        f"นรก {money_stored(player, 'hell')}",
        f" ถืออยู่  โลก {money_held(player, 'world')}  ·  "
        f"สวรรค์ {money_held(player, 'heaven')}  ·  "
        f"นรก {money_held(player, 'hell')}",
    ]
    prefs = w.get("prefs") or {}
    auto = "เปิด" if prefs.get("auto_stash") else "ปิด"
    lines.append("---")
    lines.append(
        f" Auto stash  {auto}  (mat/junk/ยา/อาหาร · ต้องเข้าคลังไว้)"
    )
    return lines


def format_warehouse_item_lines(
    player: Mapping[str, Any],
    reg: Any,
    *,
    limit: int = 40,
) -> List[str]:
    ensure_warehouse(player)  # type: ignore[arg-type]
    items = (player.get("warehouse") or {}).get("items") or {}
    ids = list(items.get("inventory_ids") or [])
    if not ids:
        return [" คลังว่าง"]
    rares = list(items.get("inventory_rarities") or [])
    lines: List[str] = [f" ของในคลัง  {len(ids)}/{slots_cap(player)}", "---"]
    from game.domain.equipment import item_by_id

    for i, iid in enumerate(ids[:limit]):
        q = _wh_qty_at(items, i)
        rid = str(rares[i] if i < len(rares) else "common")
        it = item_by_id(reg, str(iid)) or {}
        try:
            from game.domain.rarity import display_item_name

            nm = display_item_name(str(it.get("name") or iid), rid, reg)
        except Exception:
            nm = str(it.get("name") or iid)
        qty_s = f" ×{q}" if q > 1 else ""
        lines.append(f"  {i + 1}. {nm}{qty_s}")
    if len(ids) > limit:
        lines.append(f"  …และอีก {len(ids) - limit} ช่อง")
    return lines


def format_bag_deposit_lines(
    player: Mapping[str, Any],
    reg: Any,
    *,
    limit: int = 30,
) -> List[str]:
    """Numbered bag slots for deposit picker."""
    from game.domain.bag_stack import ensure_inventory_qty, qty_at
    from game.domain.equipment import item_by_id

    ensure_inventory_qty(player)  # type: ignore[arg-type]
    ids = list(player.get("inventory_ids") or [])
    if not ids:
        return [" กระเป๋าว่าง — ไม่มีของฝาก"]
    rares = list(player.get("inventory_rarities") or [])
    lines: List[str] = [" ของในกระเป๋า (เลือกเลขเพื่อฝาก)", "---"]
    for i, iid in enumerate(ids[:limit]):
        q = qty_at(player, i)
        rid = str(rares[i] if i < len(rares) else "common")
        it = item_by_id(reg, str(iid)) or {}
        try:
            from game.domain.rarity import display_item_name

            nm = display_item_name(str(it.get("name") or iid), rid, reg)
        except Exception:
            nm = str(it.get("name") or iid)
        qty_s = f" ×{q}" if q > 1 else ""
        lines.append(f"  {i + 1}. {nm}{qty_s}")
    if len(ids) > limit:
        lines.append(f"  …และอีก {len(ids) - limit} ชิ้น")
    return lines


def set_auto_stash(player: MutableMapping[str, Any], enabled: bool) -> str:
    ensure_warehouse(player)
    player["warehouse"]["prefs"]["auto_stash"] = bool(enabled)
    return "เปิด Auto stash" if enabled else "ปิด Auto stash"


def auto_stash_enabled(player: Mapping[str, Any]) -> bool:
    ensure_warehouse(player)  # type: ignore[arg-type]
    return bool((player.get("warehouse") or {}).get("prefs", {}).get("auto_stash"))


def _category_of(item_id: str, reg: Any) -> str:
    try:
        from game.domain.inventory_sys import item_category

        return str(item_category(item_id, reg) or "other")
    except Exception:
        return "other"


def can_auto_stash_item(item_id: str, reg: Any, player: Mapping[str, Any]) -> bool:
    """mat/other/healing/food; never relic/card/equipment/chest (manual OK)."""
    cfg = _cfg()
    cat = _category_of(item_id, reg)
    blocked = set(cfg.get("auto_stash_block_categories") or [])
    allowed = set(
        (player.get("warehouse") or {}).get("prefs", {}).get("auto_stash_categories")
        or cfg.get("auto_stash_categories")
        or ["material", "other", "healing", "food"]
    )
    if cat in blocked:
        return False
    if cat not in allowed:
        return False
    try:
        from game.domain.bag_sell import is_relic_item
        from game.domain.equipment import item_by_id

        it = item_by_id(reg, item_id) or {}
        if is_relic_item(str(item_id), it):
            return False
    except Exception:
        pass
    if str(item_id).startswith("card_") or (reg and item_id in (getattr(reg, "cards", None) or {})):
        return False
    return True


def auto_stash_from_bag(
    player: MutableMapping[str, Any],
    reg: Any,
    *,
    need_free: int = 2,
    max_moves: int = 4,
) -> List[str]:
    """
    When bag nearly full and auto_stash ON + vault session unlocked,
    move mat/junk/healing/food into shared vault.
    Requires prior login this session (no passwordless open).
    """
    notes: List[str] = []
    ensure_warehouse(player)
    if not auto_stash_enabled(player):
        return notes
    if not is_unlocked(player):
        return notes
    from game.runtime.inventory_auto import bag_free_slots, bag_used
    from game.domain.bag_stack import qty_at

    need = max(0, int(need_free))
    free = bag_free_slots(player)
    if free >= need:
        return notes

    ids = list(player.get("inventory_ids") or [])
    moved = 0
    i = len(ids) - 1
    while i >= 0 and moved < max_moves and bag_free_slots(player) < need:
        ids = list(player.get("inventory_ids") or [])
        if i >= len(ids):
            i -= 1
            continue
        iid = str(ids[i])
        if not can_auto_stash_item(iid, reg, player):
            i -= 1
            continue
        q = qty_at(player, i)
        ok, msg = deposit_item_at(player, i, reg, qty=q)
        if ok:
            moved += 1
            notes.append(f"  คลังทีม← {msg}")
            i -= 1
        else:
            i -= 1
    if moved:
        notes.insert(
            0,
            f" Auto stash · ย้าย {moved} ช่องเข้าคลังทีม "
            f"(กระเป๋า {bag_used(player)} ช่อง)",
        )
    return notes

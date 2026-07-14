"""In-memory content registry (P1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from game.config import DATA_DIR
from game.data_load.loader import load_dir_maps, load_file, load_list_file


@dataclass
class DataRegistry:
    areas: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    monsters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    skills: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    occupations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    items: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cards: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    shops: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    quests: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recipes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    gear_sets: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    unit_classes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    library_entries: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    library_access: Dict[str, Any] = field(default_factory=dict)
    world_social: Dict[str, Any] = field(default_factory=dict)
    personality: Dict[str, Any] = field(default_factory=dict)
    personality_grants: Dict[str, Any] = field(default_factory=dict)
    personality_tips: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    personality_tips_meta: Dict[str, Any] = field(default_factory=dict)
    npc_archetypes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    skill_masters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    party: Dict[str, Any] = field(default_factory=dict)
    narrative: Dict[str, Any] = field(default_factory=dict)
    rarity: Dict[str, Any] = field(default_factory=dict)
    dungeons_cfg: Dict[str, Any] = field(default_factory=dict)
    statuses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    status_defaults: Dict[str, Any] = field(default_factory=dict)
    worlds: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    levels: Dict[str, Any] = field(default_factory=dict)
    matchups: List[Dict[str, Any]] = field(default_factory=list)
    fusions_cfg: Dict[str, Any] = field(default_factory=dict)
    approach: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    blessings: Dict[str, Any] = field(default_factory=dict)
    class_paths: Dict[str, Any] = field(default_factory=dict)
    mission_board: Dict[str, Any] = field(default_factory=dict)
    root: Path = DATA_DIR

    @classmethod
    def load(cls, root: Optional[Path] = None) -> "DataRegistry":
        root = root or DATA_DIR
        reg = cls(root=root)
        reg.areas = load_dir_maps(root / "areas")
        mon_path = root / "monsters" / "monsters.yaml"
        if mon_path.exists():
            reg.monsters = load_list_file(mon_path)
        else:
            reg.monsters = load_dir_maps(root / "monsters")
        # Skills: merge all YAML lists under data/skills/ except masters.yaml
        skills_dir = root / "skills"
        reg.skills = {}
        if skills_dir.is_dir():
            for path in sorted(skills_dir.iterdir()):
                if path.suffix.lower() not in {".yaml", ".yml"}:
                    continue
                if path.name.startswith("."):
                    continue
                if path.name in ("masters.yaml", "catalog_meta.yaml"):
                    continue
                part = load_list_file(path)
                for sid, sk in part.items():
                    sk = dict(sk)
                    sk.setdefault("id", sid)
                    reg.skills[sid] = sk
        if not reg.skills:
            sk_path = skills_dir / "skills.yaml"
            if sk_path.exists():
                reg.skills = load_list_file(sk_path)
        masters_path = skills_dir / "masters.yaml"
        if masters_path.exists():
            reg.skill_masters = load_list_file(masters_path)
        occ_path = root / "occupations" / "occupations.yaml"
        if occ_path.exists():
            reg.occupations = load_list_file(occ_path)
        else:
            reg.occupations = load_dir_maps(root / "occupations")
        cp_path = root / "occupations" / "class_paths.yaml"
        if cp_path.exists():
            cpd = load_file(cp_path)
            if isinstance(cpd, dict):
                reg.class_paths = cpd
        bless_path = root / "blessings" / "blessings.yaml"
        if bless_path.exists():
            bd = load_file(bless_path)
            if isinstance(bd, dict):
                reg.blessings = bd
        mission_path = root / "missions" / "board.yaml"
        if mission_path.exists():
            md = load_file(mission_path)
            if isinstance(md, dict):
                reg.mission_board = md
        it_path = root / "items" / "items.yaml"
        if it_path.exists():
            reg.items = load_list_file(it_path)
        else:
            reg.items = load_dir_maps(root / "items")
        cards_path = root / "cards" / "cards.yaml"
        if cards_path.exists():
            reg.cards = load_list_file(cards_path)
            # mark kind for convenience
            for cid, card in reg.cards.items():
                card.setdefault("kind", "card")
                card.setdefault("id", cid)
        shops_path = root / "shops" / "shops.yaml"
        if shops_path.exists():
            reg.shops = load_list_file(shops_path)
        else:
            reg.shops = load_dir_maps(root / "shops")
        quests_path = root / "quests" / "quests.yaml"
        if quests_path.exists():
            reg.quests = load_list_file(quests_path)
        recipes_path = root / "craft" / "recipes.yaml"
        if recipes_path.exists():
            reg.recipes = load_list_file(recipes_path)
        sets_path = root / "sets" / "gear_sets.yaml"
        if sets_path.exists():
            reg.gear_sets = load_list_file(sets_path)
        unit_path = root / "occupations" / "unit_classes.yaml"
        if unit_path.exists():
            reg.unit_classes = load_list_file(unit_path)
        lib_ent = root / "library" / "entries.yaml"
        if lib_ent.exists():
            reg.library_entries = load_list_file(lib_ent)
        lib_acc = root / "library" / "access.yaml"
        if lib_acc.exists():
            data = load_file(lib_acc)
            if isinstance(data, dict):
                reg.library_access = data
        reg.worlds = load_dir_maps(root / "worlds")
        social_path = root / "worlds" / "social.yaml"
        if social_path.exists():
            sdata = load_file(social_path)
            if isinstance(sdata, dict):
                reg.world_social = sdata
        # keep only real playable worlds (have difficulty / starting_area)
        reg.worlds = {
            k: v
            for k, v in reg.worlds.items()
            if isinstance(v, dict)
            and v.get("starting_area")
            and k not in ("social",)
            and v.get("id") != "world_social"
        }
        levels_path = root / "levels.yaml"
        if levels_path.exists():
            data = load_file(levels_path)
            reg.levels = data if isinstance(data, dict) else {}
        match_path = root / "elements" / "matchups.yaml"
        if match_path.exists():
            data = load_file(match_path)
            if isinstance(data, dict):
                reg.matchups = list(data.get("matchups") or [])
        fusion_path = root / "elements" / "fusions.yaml"
        if fusion_path.exists():
            data = load_file(fusion_path)
            if isinstance(data, dict):
                reg.fusions_cfg = data
        approach_path = root / "encounters" / "approach.yaml"
        if approach_path.exists():
            data = load_file(approach_path)
            if isinstance(data, dict):
                reg.approach = {
                    k: list(v) if isinstance(v, list) else []
                    for k, v in data.items()
                    if k != "placeholder"
                }
        pers_path = root / "personality" / "traits.yaml"
        if pers_path.exists():
            data = load_file(pers_path)
            if isinstance(data, dict):
                reg.personality = data
        grants_path = root / "personality" / "point_grants.yaml"
        if grants_path.exists():
            data = load_file(grants_path)
            if isinstance(data, dict):
                reg.personality_grants = data
        tips_path = root / "library" / "personality_tips.yaml"
        if tips_path.exists():
            data = load_file(tips_path)
            if isinstance(data, list):
                reg.personality_tips = {
                    str(x.get("id")): x for x in data if isinstance(x, dict) and x.get("id")
                }
                reg.personality_tips_meta = {"personality_tip_chance": 0.55}
            elif isinstance(data, dict):
                meta = {
                    "personality_tip_chance": float(
                        data.get("personality_tip_chance", 0.55)
                    )
                }
                reg.personality_tips_meta = meta
                tips_list = data.get("tips") or []
                if isinstance(tips_list, list):
                    reg.personality_tips = {
                        str(x.get("id")): x
                        for x in tips_list
                        if isinstance(x, dict) and x.get("id")
                    }
                else:
                    # fallback: treat top-level dict values with id as tips
                    reg.personality_tips = {
                        str(v.get("id")): v
                        for k, v in data.items()
                        if isinstance(v, dict) and v.get("id")
                    }
        if not reg.personality_tips_meta:
            reg.personality_tips_meta = {"personality_tip_chance": 0.55}
        npc_arch = root / "personality" / "npc_archetypes.yaml"
        if npc_arch.exists():
            reg.npc_archetypes = load_list_file(npc_arch)
        party_path = root / "party" / "companions.yaml"
        if party_path.exists():
            data = load_file(party_path)
            if isinstance(data, dict):
                reg.party = data
        # Narrative: merge all YAML under data/narrative/
        narr_dir = root / "narrative"
        reg.narrative = {}
        if narr_dir.is_dir():
            for path in sorted(narr_dir.iterdir()):
                if path.suffix.lower() not in {".yaml", ".yml"}:
                    continue
                data = load_file(path)
                if isinstance(data, dict):
                    # later files override same keys; lists replace
                    reg.narrative.update(data)
        rarity_path = root / "rarity" / "tiers.yaml"
        if rarity_path.exists():
            data = load_file(rarity_path)
            if isinstance(data, dict):
                reg.rarity = data
        dung_path = root / "dungeons" / "dungeons.yaml"
        if dung_path.exists():
            data = load_file(dung_path)
            if isinstance(data, dict):
                reg.dungeons_cfg = data
        # Status catalog: data/statuses/statuses.yaml (list or map)
        st_path = root / "statuses" / "statuses.yaml"
        if st_path.exists():
            data = load_file(st_path)
            if isinstance(data, dict):
                reg.status_defaults = dict(data.get("defaults") or {})
                raw = data.get("statuses")
                if isinstance(raw, list):
                    for entry in raw:
                        if isinstance(entry, dict) and entry.get("id"):
                            sid = str(entry["id"])
                            e = dict(entry)
                            e.setdefault("id", sid)
                            reg.statuses[sid] = e
                elif isinstance(raw, dict):
                    for sid, entry in raw.items():
                        if isinstance(entry, dict):
                            e = dict(entry)
                            e.setdefault("id", sid)
                            reg.statuses[str(sid)] = e
            elif isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict) and entry.get("id"):
                        sid = str(entry["id"])
                        reg.statuses[sid] = dict(entry)
        reg._validate()
        return reg

    def _validate(self) -> None:
        if not self.areas:
            raise ValueError("No areas loaded from data/areas")
        if not self.occupations:
            raise ValueError("No occupations loaded")
        for area in self.areas.values():
            for entry in area.get("monster_pools") or []:
                mid = entry.get("id")
                if mid and mid not in self.monsters:
                    raise ValueError(
                        f"Area {area.get('id')} references unknown monster {mid}"
                    )
        for occ in self.occupations.values():
            sk = occ.get("skill")
            if sk and sk not in self.skills:
                raise ValueError(f"Occupation skill missing: {sk}")

    def area_name(self, area_id: str) -> str:
        if str(area_id).startswith("dungeon:"):
            did = str(area_id).split(":", 1)[-1]
            for d in (self.dungeons_cfg or {}).get("dungeons") or []:
                if str(d.get("id")) == did:
                    return str(d.get("name") or did)
        a = self.areas.get(area_id) or {}
        return str(a.get("name") or area_id)

    def skill_name(self, skill_id: str) -> str:
        s = self.skills.get(skill_id) or {}
        return str(s.get("name") or skill_id)

    def element_mult(self, attack_elems: List[str], defend_elems: List[str]) -> float:
        mult = 1.0
        for rule in self.matchups:
            if rule.get("attacker") in attack_elems and rule.get("defender") in defend_elems:
                mult *= float(rule.get("mult", 1.0))
        return mult


_REGISTRY: Optional[DataRegistry] = None


def get_registry(reload: bool = False) -> DataRegistry:
    global _REGISTRY
    if _REGISTRY is None or reload:
        _REGISTRY = DataRegistry.load()
    return _REGISTRY

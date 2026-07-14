"""Load YAML/JSON content files into plain Python structures."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def load_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                f"PyYAML required to load {path.name}. pip install PyYAML"
            )
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    raise ValueError(f"Unsupported data file: {path}")


def load_dir_maps(directory: Path, key: str = "id") -> Dict[str, Dict[str, Any]]:
    """Load all yaml/json in a directory into id -> record map."""
    out: Dict[str, Dict[str, Any]] = {}
    if not directory.is_dir():
        return out
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        if path.name.startswith("."):
            continue
        data = load_file(path)
        if data is None:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and key in item:
                    out[str(item[key])] = item
        elif isinstance(data, dict):
            if key in data:
                out[str(data[key])] = data
            else:
                # mapping file of id -> obj
                for k, v in data.items():
                    if isinstance(v, dict):
                        v = {**v, key: v.get(key, k)}
                        out[str(v[key])] = v
    return out


def load_list_file(path: Path, key: str = "id") -> Dict[str, Dict[str, Any]]:
    data = load_file(path)
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and key in item:
                out[str(item[key])] = item
    elif isinstance(data, dict) and key in data:
        out[str(data[key])] = data
    return out

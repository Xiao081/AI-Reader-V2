"""Versioned, title-scoped curated entity dictionary presets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.models.entity_dict import EntityDictEntry


_PRESET_DIR = Path(__file__).resolve().parents[1] / "resources" / "entity_presets"
_PRESET_FILES = {
    "douluo1-curated-v2": _PRESET_DIR / "douluo1-curated-v2.json",
}


@lru_cache(maxsize=None)
def load_preset(preset_id: str) -> dict:
    """Load and validate a packaged preset without touching user data."""
    path = _PRESET_FILES.get(preset_id)
    if path is None or not path.is_file():
        raise KeyError(preset_id)

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("id") != preset_id:
        raise ValueError(f"preset id mismatch: {preset_id}")

    entries = [EntityDictEntry.model_validate(item) for item in data.get("entries", [])]
    names = [entry.name for entry in entries]
    if not entries or len(names) != len(set(names)):
        raise ValueError(f"preset {preset_id} is empty or has duplicate names")

    return {**data, "entries": entries}


def is_compatible(preset: dict, novel_title: str) -> bool:
    """Return whether a preset is explicitly scoped to this novel title."""
    normalized = (novel_title or "").replace(" ", "")
    includes = preset.get("title_include", [])
    excludes = preset.get("title_exclude", [])
    return (
        bool(normalized)
        and all(marker.replace(" ", "") in normalized for marker in includes)
        and not any(marker.replace(" ", "") in normalized for marker in excludes)
    )


def get_compatible_presets(novel_title: str) -> list[dict]:
    """Return public metadata for presets matching the supplied title."""
    result = []
    for preset_id in _PRESET_FILES:
        preset = load_preset(preset_id)
        if is_compatible(preset, novel_title):
            result.append(
                {
                    "id": preset["id"],
                    "version": preset["version"],
                    "label": preset["label"],
                    "description": preset["description"],
                    "entry_count": len(preset["entries"]),
                }
            )
    return result


async def apply_preset(novel_id: str, novel_title: str, preset_id: str) -> int:
    """Replace one compatible novel's dictionary with a packaged preset."""
    preset = load_preset(preset_id)
    if not is_compatible(preset, novel_title):
        raise ValueError("preset is not compatible with this novel")

    from src.db import entity_dictionary_store
    from src.services import entity_aggregator

    count = await entity_dictionary_store.replace_all(novel_id, preset["entries"])
    entity_aggregator.invalidate_cache(novel_id)
    return count

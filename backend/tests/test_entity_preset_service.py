"""Tests for title-scoped curated entity dictionary presets."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.db import entity_dictionary_store
from src.models.entity_dict import EntityDictEntry
from src.services.entity_preset_service import (
    get_compatible_presets,
    is_compatible,
    load_preset,
)
from src.extraction.context_summary_builder import ContextSummaryBuilder


PRESET_ID = "douluo1-curated-v1"


def test_douluo1_preset_is_curated_and_unique():
    preset = load_preset(PRESET_ID)
    entries = preset["entries"]
    by_name = {entry.name: entry for entry in entries}

    assert len(entries) == 83
    assert len(by_name) == len(entries)
    assert by_name["玉小刚"].aliases == ["大师", "小刚"]
    assert by_name["蓝银草"].entity_type == "item"
    assert by_name["八蛛矛"].entity_type == "item"
    assert by_name["人面魔蛛"].entity_type == "concept"

    # Known segmentation noise and globally ambiguous offices stay out.
    assert "三身体" not in by_name
    assert "银草" not in by_name
    assert "院长" not in by_name
    assert "宗主" not in by_name
    assert "教皇" not in by_name


@pytest.mark.asyncio
async def test_curated_preset_reaches_analysis_context(monkeypatch):
    preset = load_preset(PRESET_ID)

    async def get_all(_novel_id: str):
        return preset["entries"]

    monkeypatch.setattr(entity_dictionary_store, "get_all", get_all)
    section = await ContextSummaryBuilder()._build_dictionary_section("novel-1")

    assert "玉小刚（person" in section
    assert "可能别名：大师、小刚" in section
    assert "蓝银草（item" in section
    assert "人面魔蛛（concept" in section
    assert "三身体" not in section
    assert "院长（person" not in section


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("《斗罗大陆》（校对版全本）作者：唐家三少", True),
        ("斗罗大陆1", True),
        ("斗罗大陆2 绝世唐门", False),
        ("斗罗大陆Ⅲ 龙王传说", False),
        ("终极斗罗", False),
        ("随机小说", False),
    ],
)
def test_douluo1_preset_title_scope(title: str, expected: bool):
    preset = load_preset(PRESET_ID)
    assert is_compatible(preset, title) is expected
    assert bool(get_compatible_presets(title)) is expected


@pytest.mark.asyncio
async def test_replace_all_is_atomic_and_marks_prescan_complete(memory_db):
    novel_id = "douluo-test"
    await memory_db.execute(
        "INSERT INTO novels (id, title, prescan_status) VALUES (?, ?, ?)",
        (novel_id, "斗罗大陆1", "failed"),
    )
    await memory_db.execute(
        """
        INSERT INTO entity_dictionary
            (novel_id, name, entity_type, frequency, confidence, aliases, source, sample_context)
        VALUES (?, '三身体', 'person', 100, 'high', '[]', 'dialogue', '')
        """,
        (novel_id,),
    )
    await memory_db.commit()

    class NonClosingConnection:
        def __init__(self, conn):
            self._conn = conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        async def close(self):
            pass

    async def get_connection():
        return NonClosingConnection(memory_db)

    entries = [
        EntityDictEntry(
            name="玉小刚",
            entity_type="person",
            frequency=100,
            confidence="high",
            aliases=["大师"],
            source=f"preset:{PRESET_ID}",
            sample_context="大师",
        ),
        EntityDictEntry(
            name="蓝银草",
            entity_type="item",
            frequency=80,
            confidence="high",
            aliases=[],
            source=f"preset:{PRESET_ID}",
            sample_context="蓝银草",
        ),
    ]

    with patch.object(entity_dictionary_store, "get_connection", get_connection):
        count = await entity_dictionary_store.replace_all(novel_id, entries)

    assert count == 2
    rows = await memory_db.execute_fetchall(
        "SELECT name, source FROM entity_dictionary WHERE novel_id = ? ORDER BY name",
        (novel_id,),
    )
    assert [(row[0], row[1]) for row in rows] == [
        ("玉小刚", f"preset:{PRESET_ID}"),
        ("蓝银草", f"preset:{PRESET_ID}"),
    ]
    status = await memory_db.execute_fetchall(
        "SELECT prescan_status FROM novels WHERE id = ?",
        (novel_id,),
    )
    assert status[0][0] == "completed"

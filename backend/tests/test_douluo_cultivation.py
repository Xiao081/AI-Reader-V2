from src.extraction.fact_validator import FactValidator
from src.models.chapter_fact import ChapterFact, CultivationEventFact


def test_cultivation_event_requires_verbatim_chapter_evidence():
    text = "唐三抬起右手，掌心出现了蓝银草，这是他的武魂。"
    valid = CultivationEventFact(
        character="唐三",
        event_type="武魂揭示",
        martial_soul="蓝银草",
        evidence="掌心出现了蓝银草，这是他的武魂",
    )
    leaked = CultivationEventFact(
        character="唐三",
        event_type="武魂揭示",
        martial_soul="昊天锤",
        evidence="唐三拥有昊天锤",
    )
    fact = ChapterFact(
        chapter_id=1,
        novel_id="douluo",
        cultivation_events=[valid, leaked],
    )

    cleaned = FactValidator().validate(fact, text)

    assert [event.martial_soul for event in cleaned.cultivation_events] == ["蓝银草"]


def test_legacy_chapter_fact_defaults_to_no_cultivation_events():
    fact = ChapterFact.model_validate({"chapter_id": 1, "novel_id": "legacy"})
    assert fact.cultivation_events == []

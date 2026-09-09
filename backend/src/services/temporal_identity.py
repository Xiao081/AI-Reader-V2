"""Chapter-bounded presentation names for already-resolved person identities.

Alias resolution answers whether two mentions are the same underlying entity.
This module answers a separate question: which name was narratively available
at a chapter cutoff?  Keeping the two decisions separate prevents future-name
leakage without breaking cross-chapter graph connectivity.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable, Protocol

from src.models.chapter_fact import ChapterFact


class _AsyncConnection(Protocol):
    async def execute(self, sql: str, parameters: tuple[object, ...]): ...
    async def close(self) -> None: ...


async def load_temporal_identity_rules(
    novel_id: str,
    connection_factory: Callable[[], Awaitable[_AsyncConnection]],
) -> dict[str, dict[str, object]]:
    """Load title-scoped presentation rules through the caller's DB boundary."""
    from src.services.person_knowledge_prior import get_temporal_identity_rules

    conn = await connection_factory()
    try:
        cursor = await conn.execute("SELECT title FROM novels WHERE id = ?", (novel_id,))
        row = await cursor.fetchone()
        return get_temporal_identity_rules(row["title"] if row else "")
    finally:
        await conn.close()


@dataclass(frozen=True)
class IdentityPresentation:
    canonical_name: str
    display_name: str
    observed_names: frozenset[str]
    visible_names: frozenset[str]
    reveal_chapter: int | None = None
    identity_kind: str = "alias"


def build_temporal_alias_map(
    alias_map: dict[str, str],
    as_of_chapter: int,
    temporal_rules: dict[str, dict[str, object]] | None = None,
) -> dict[str, str]:
    """Return an alias map that defers persona merges until their reveal.

    Before a reveal, an early persona remains its own graph identity.  This is
    necessary when the real person is independently mentioned in the story
    before anyone knows that the persona belongs to them (唐晨/杀戮之王).
    """
    result = dict(alias_map)
    for canonical, rule in (temporal_rules or {}).items():
        reveal_chapter = int(rule["reveal_chapter"])
        if as_of_chapter >= reveal_chapter:
            continue
        early_names = tuple(str(n) for n in rule.get("early_names", ()))
        if not early_names:
            continue
        early_identity = early_names[0]
        for name in early_names:
            result[name] = early_identity
        result[early_identity] = early_identity
        result[canonical] = canonical
    return result


def _person_mentions(fact: ChapterFact) -> Iterable[str]:
    for char in fact.characters:
        yield char.name
    for rel in fact.relationships:
        yield rel.person_a
        yield rel.person_b
    for event in fact.events:
        yield from event.participants
    for item_event in fact.item_events:
        if item_event.actor:
            yield item_event.actor
        if item_event.recipient:
            yield item_event.recipient
    for org_event in fact.org_events:
        if org_event.member:
            yield org_event.member


def build_identity_presentations(
    facts: list[ChapterFact],
    alias_map: dict[str, str],
    as_of_chapter: int,
    temporal_rules: dict[str, dict[str, object]] | None = None,
) -> dict[str, IdentityPresentation]:
    """Build canonical -> chapter-safe presentation metadata.

    The generic rule uses the canonical name once it has actually appeared by
    the cutoff; otherwise it uses the most frequent observed alias.  Explicit
    rules handle disguises whose canonical person may be mentioned elsewhere
    before the narrative reveals that the identities are connected.
    """
    temporal_rules = temporal_rules or {}
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    first_seen: dict[tuple[str, str], int] = {}

    for fact in facts:
        if fact.chapter_id > as_of_chapter:
            continue
        for raw_name in _person_mentions(fact):
            name = raw_name.strip()
            if not name:
                continue
            canonical = alias_map.get(name, name)
            counts[canonical][name] += 1
            first_seen.setdefault((canonical, name), fact.chapter_id)

    presentations: dict[str, IdentityPresentation] = {}
    for canonical, name_counts in counts.items():
        observed = frozenset(name_counts)
        rule = temporal_rules.get(canonical)
        reveal_chapter = int(rule["reveal_chapter"]) if rule else None
        identity_kind = str(rule.get("kind", "alias")) if rule else "alias"

        display_name = canonical
        visible_names = observed
        if rule and as_of_chapter < reveal_chapter:
            early_names = tuple(str(n) for n in rule.get("early_names", ()))
            available = [n for n in early_names if n in observed]
            if available:
                display_name = max(
                    available,
                    key=lambda n: (name_counts[n], -first_seen[(canonical, n)]),
                )
                visible_names = frozenset(available)
        # Unconfigured aliases keep the established canonical presentation.
        # Temporal presentation is opt-in because a normal nickname is not a
        # hidden identity and changing it would destabilize existing graphs.

        presentations[canonical] = IdentityPresentation(
            canonical_name=canonical,
            display_name=display_name,
            observed_names=observed,
            visible_names=visible_names,
            reveal_chapter=reveal_chapter,
            identity_kind=identity_kind,
        )

    return presentations


def display_name_for(
    canonical_name: str,
    presentations: dict[str, IdentityPresentation],
) -> str:
    presentation = presentations.get(canonical_name)
    return presentation.display_name if presentation else canonical_name

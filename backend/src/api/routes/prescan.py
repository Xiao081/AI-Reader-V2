"""Pre-scan and entity dictionary endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.db import entity_dictionary_store, novel_store

router = APIRouter(prefix="/api", tags=["prescan"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class EntityPresetInfo(BaseModel):
    id: str
    version: int
    label: str
    description: str
    entry_count: int
    applied: bool = False


class PrescanStatusResponse(BaseModel):
    status: str
    entity_count: int
    created_at: str | None = None
    preset: EntityPresetInfo | None = None


class ApplyEntityPresetResponse(BaseModel):
    status: str
    preset_id: str
    entity_count: int


class EntityDictItem(BaseModel):
    name: str
    entity_type: str
    frequency: int
    confidence: str
    aliases: list[str]
    source: str
    sample_context: str | None = None


class EntityDictionaryResponse(BaseModel):
    data: list[EntityDictItem]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/novels/{novel_id}/prescan")
async def trigger_prescan(novel_id: str):
    """Manually trigger a pre-scan. Returns 409 if already running."""
    novel = await novel_store.get_novel(novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    status = await entity_dictionary_store.get_prescan_status(novel_id)
    if status == "running":
        raise HTTPException(status_code=409, detail="预扫描正在进行中")

    # If completed, delete existing and re-scan
    if status == "completed":
        await entity_dictionary_store.delete_all(novel_id)

    # Trigger in background
    async def _run() -> None:
        from src.extraction.entity_pre_scanner import EntityPreScanner
        scanner = EntityPreScanner()
        await scanner.scan(novel_id)

    asyncio.create_task(_run())

    return {"status": "running"}


@router.get("/novels/{novel_id}/prescan", response_model=PrescanStatusResponse)
async def get_prescan_status(novel_id: str):
    """Query pre-scan status and entity count."""
    novel = await novel_store.get_novel(novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    status = await entity_dictionary_store.get_prescan_status(novel_id)
    entries = await entity_dictionary_store.get_all(novel_id)
    from src.services.entity_preset_service import get_compatible_presets

    presets = get_compatible_presets(novel.get("title", ""))
    preset_info = None
    if presets:
        preset = presets[0]
        preset_info = EntityPresetInfo(
            **preset,
            applied=(
                len(entries) == preset["entry_count"]
                and all(e.source == f"preset:{preset['id']}" for e in entries)
            ),
        )

    return PrescanStatusResponse(
        status=status,
        entity_count=len(entries),
        created_at=novel.get("created_at"),
        preset=preset_info,
    )


@router.post(
    "/novels/{novel_id}/entity-presets/{preset_id}",
    response_model=ApplyEntityPresetResponse,
)
async def apply_entity_preset(novel_id: str, preset_id: str):
    """Atomically replace a compatible novel's dictionary with a preset."""
    novel = await novel_store.get_novel(novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    status = await entity_dictionary_store.get_prescan_status(novel_id)
    if status == "running":
        raise HTTPException(status_code=409, detail="预扫描运行中，不能替换词表")

    from src.db import analysis_task_store
    active_task = await analysis_task_store.get_running_task(novel_id)
    if active_task:
        raise HTTPException(status_code=409, detail="分析运行或暂停中，不能替换词表")

    from src.services.entity_preset_service import apply_preset, load_preset

    try:
        load_preset(preset_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="词表预设不存在") from None
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"词表预设无效：{exc}") from exc

    try:
        count = await apply_preset(novel_id, novel.get("title", ""), preset_id)
    except ValueError:
        raise HTTPException(status_code=409, detail="该词表预设不适用于当前小说") from None

    return ApplyEntityPresetResponse(
        status="completed",
        preset_id=preset_id,
        entity_count=count,
    )


@router.get(
    "/novels/{novel_id}/entity-dictionary",
    response_model=EntityDictionaryResponse,
)
async def get_entity_dictionary(
    novel_id: str,
    type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get entity dictionary contents."""
    novel = await novel_store.get_novel(novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    if type:
        entries = await entity_dictionary_store.get_by_type(novel_id, type, limit)
    else:
        entries = await entity_dictionary_store.get_all(novel_id)
        entries = entries[:limit]

    data = [
        EntityDictItem(
            name=e.name,
            entity_type=e.entity_type,
            frequency=e.frequency,
            confidence=e.confidence,
            aliases=e.aliases,
            source=e.source,
            sample_context=e.sample_context,
        )
        for e in entries
    ]

    return EntityDictionaryResponse(data=data, total=len(data))

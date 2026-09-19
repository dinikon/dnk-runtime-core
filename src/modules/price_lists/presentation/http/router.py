from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

import uuid6
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, HttpUrl

from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.price_lists.application import (
    PriceListService,
    PriceListStateConflict,
    cron_occurrences,
    next_cron_occurrence,
)
from src.modules.price_lists.domain import (
    deterministic_cleanup_job_id,
    deterministic_job_id,
)
from src.modules.price_lists.infrastructure.persistence import (
    SqlAlchemyPriceListRepository,
)
from src.modules.shared.domain.identity_context import RequestContext
from src.modules.shared.domain.jobs import ScheduledJob, ScheduledJobStatus
from src.modules.shared.presentation.jobs import build_scheduled_job_repository
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep

router = APIRouter(prefix="/price-lists", tags=["price-lists"])
offers_router = APIRouter(prefix="/price-list-offers", tags=["price-list-offers"])


class CreatePriceListRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl
    source_format: Literal["xml", "yaml", "xlsx"]
    source_preset: Literal["prom_xml"] | None = None
    source_config: dict[str, Any] = Field(default_factory=dict)


class MappingRequest(BaseModel):
    source_config: dict[str, Any]
    mapping_config: dict[str, Any]


class PreviewPriceListRequest(BaseModel):
    source_url: HttpUrl | None = None
    source_format: Literal["xml", "yaml", "xlsx"] | None = None
    source_preset: Literal["prom_xml"] | None = None
    source_config: dict[str, Any] | None = None
    mapping_config: dict[str, Any] | None = None


class ScheduleRequest(BaseModel):
    cron_expression: str = Field(min_length=5, max_length=128)
    timezone: str = Field(default="Europe/Kyiv", max_length=64)
    new_item_policy: Literal["create", "quarantine", "ignore"] = "create"
    missing_item_policy: Literal[
        "mark_out_of_stock", "mark_missing", "keep_last", "archive"
    ] = "mark_out_of_stock"
    missing_threshold: int = Field(default=2, ge=1, le=100)


class UpdatePriceListSettingsRequest(ScheduleRequest):
    title: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl | None = None
    source_format: Literal["xml", "yaml", "xlsx"]
    source_preset: Literal["prom_xml"] | None = None
    source_config: dict[str, Any]
    mapping_config: dict[str, Any]


class DeletePriceListRequest(BaseModel):
    confirmation_title: str = Field(min_length=1, max_length=255)


def _ids(context: RequestContext) -> tuple[UUID, UUID]:
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tenant context is required.")
    return UUID(principal.tenant_id), UUID(principal.user_id)


def _public_price_list(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"source_url_secret", "created_by", "updated_by"}
    }


def _job(
    *,
    job_id: UUID,
    tenant_id: UUID,
    price_list_id: UUID,
    revision: int,
    run_at: datetime,
    trigger: str,
) -> ScheduledJob:
    now = datetime.now(UTC)
    return ScheduledJob(
        id=job_id,
        tenant_id=tenant_id,
        job_type="price_list.sync",
        payload={
            "price_list_id": str(price_list_id),
            "schedule_revision": revision,
            "planned_at": run_at.isoformat(),
            "trigger": trigger,
        },
        run_at=run_at,
        status=ScheduledJobStatus.SCHEDULED.value,
        attempts=0,
        locked_until=None,
        lock_token=None,
        created_at=now,
        updated_at=now,
    )


@router.post(
    "", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)]
)
async def create_price_list(
    payload: CreatePriceListRequest,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    service = PriceListService(SqlAlchemyPriceListRepository(uow.session))
    try:
        price_list_id = await service.create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            title=payload.title,
            source_format=payload.source_format,
            source_preset=payload.source_preset,
            source_url=str(payload.source_url),
            source_config=payload.source_config,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"id": price_list_id}


@router.get("")
async def list_price_lists(
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
    scope: Literal["current", "archived", "all"] = "current",
):
    tenant_id, _ = _ids(context)
    rows = await SqlAlchemyPriceListRepository(uow.session).list(tenant_id, scope=scope)
    return {"items": [_public_price_list(row) for row in rows]}


@router.get("/schedule-preview")
async def preview_schedule(
    context: AuthenticatedRequestContextDep,
    expression: str = Query(min_length=5, max_length=128),
    timezone: str = Query(default="Europe/Kyiv", max_length=64),
):
    _ids(context)
    try:
        occurrences = cron_occurrences(expression, timezone)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"occurrences": occurrences}


@router.get("/{price_list_id}")
async def get_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, _ = _ids(context)
    row = await SqlAlchemyPriceListRepository(uow.session).get(tenant_id, price_list_id)
    if row is None:
        raise HTTPException(404, "Price list not found.")
    return _public_price_list(row)


@router.post("/{price_list_id}/preview", dependencies=[Depends(require_csrf)])
async def preview_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
    payload: PreviewPriceListRequest | None = None,
):
    tenant_id, _ = _ids(context)
    try:
        return await PriceListService(
            SqlAlchemyPriceListRepository(uow.session)
        ).preview(
            tenant_id,
            price_list_id,
            candidate=(
                payload.model_dump(exclude_unset=True, mode="json")
                if payload is not None
                else None
            ),
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, f"Preview failed: {type(exc).__name__}") from exc


@router.put("/{price_list_id}/mapping", dependencies=[Depends(require_csrf)])
async def save_mapping(
    price_list_id: UUID,
    payload: MappingRequest,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    try:
        await PriceListService(SqlAlchemyPriceListRepository(uow.session)).save_mapping(
            tenant_id=tenant_id,
            actor_id=actor_id,
            price_list_id=price_list_id,
            source_config=payload.source_config,
            mapping_config=payload.mapping_config,
        )
    except PriceListStateConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ValueError, LookupError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"status": "ready"}


@router.put("/{price_list_id}/schedule", dependencies=[Depends(require_csrf)])
async def save_schedule(
    price_list_id: UUID,
    payload: ScheduleRequest,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    try:
        next_at = await PriceListService(
            SqlAlchemyPriceListRepository(uow.session)
        ).save_schedule(
            tenant_id=tenant_id,
            actor_id=actor_id,
            price_list_id=price_list_id,
            **payload.model_dump(),
        )
    except PriceListStateConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ValueError, LookupError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"next_sync_at": next_at}


@router.put("/{price_list_id}/settings", dependencies=[Depends(require_csrf)])
async def update_price_list_settings(
    price_list_id: UUID,
    payload: UpdatePriceListSettingsRequest,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    values = payload.model_dump(mode="json")
    source_url = values.pop("source_url", None)
    try:
        await PriceListService(
            SqlAlchemyPriceListRepository(uow.session)
        ).update_settings(
            tenant_id=tenant_id,
            actor_id=actor_id,
            price_list_id=price_list_id,
            source_url=source_url,
            **values,
        )
    except PriceListStateConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"status": "saved"}


@router.post(
    "/{price_list_id}/activate",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def activate_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    repository = SqlAlchemyPriceListRepository(uow.session)
    row = await repository.get(tenant_id, price_list_id)
    if row is None:
        raise HTTPException(404, "Price list not found.")
    if row["status"] == "active":
        raise HTTPException(409, "Price list is already active.")
    if row["status"] != "ready":
        raise HTTPException(409, "Price list mapping must be validated first.")
    if not row["mapping_config"] or not row["cron_expression"]:
        raise HTTPException(409, "Mapping and schedule must be configured first.")
    revision = int(row["schedule_revision"]) + 1
    run_at = datetime.now(UTC)
    next_at = next_cron_occurrence(
        row["cron_expression"], row["timezone"], after=run_at
    )
    job_id = uuid6.uuid7()
    await repository.update_config(
        tenant_id=tenant_id,
        actor_id=actor_id,
        price_list_id=price_list_id,
        values={
            "status": "active",
            "schedule_revision": revision,
            "next_sync_at": next_at,
        },
    )
    await build_scheduled_job_repository(uow.session).schedule_once(
        _job(
            job_id=job_id,
            tenant_id=tenant_id,
            price_list_id=price_list_id,
            revision=revision,
            run_at=run_at,
            trigger="initial",
        )
    )
    next_job_id = deterministic_job_id(
        tenant_id, price_list_id, revision, next_at.isoformat()
    )
    await build_scheduled_job_repository(uow.session).schedule_once(
        _job(
            job_id=next_job_id,
            tenant_id=tenant_id,
            price_list_id=price_list_id,
            revision=revision,
            run_at=next_at,
            trigger="cron",
        )
    )
    cleanup_at = (run_at + timedelta(days=1)).replace(
        hour=3, minute=0, second=0, microsecond=0
    )
    now = datetime.now(UTC)
    await build_scheduled_job_repository(uow.session).schedule_once(
        ScheduledJob(
            id=deterministic_cleanup_job_id(tenant_id, cleanup_at.isoformat()),
            tenant_id=tenant_id,
            job_type="price_list.cleanup",
            payload={"planned_at": cleanup_at.isoformat()},
            run_at=cleanup_at,
            status=ScheduledJobStatus.SCHEDULED.value,
            attempts=0,
            locked_until=None,
            lock_token=None,
            created_at=now,
            updated_at=now,
        )
    )
    return {"job_id": job_id, "status": "queued"}


@router.post(
    "/{price_list_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def sync_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, _ = _ids(context)
    row = await SqlAlchemyPriceListRepository(uow.session).get(tenant_id, price_list_id)
    if row is None:
        raise HTTPException(404, "Price list not found.")
    if row["status"] != "active":
        raise HTTPException(409, "Only active price lists can be synchronized.")
    job_id = uuid6.uuid7()
    await build_scheduled_job_repository(uow.session).schedule(
        _job(
            job_id=job_id,
            tenant_id=tenant_id,
            price_list_id=price_list_id,
            revision=int(row["schedule_revision"]),
            run_at=datetime.now(UTC),
            trigger="manual",
        )
    )
    return {"job_id": job_id, "status": "queued"}


@router.post("/{price_list_id}/pause", dependencies=[Depends(require_csrf)])
async def pause_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    repository = SqlAlchemyPriceListRepository(uow.session)
    row = await repository.get(tenant_id, price_list_id)
    if row is None:
        raise HTTPException(404, "Price list not found.")
    if row["status"] != "active":
        raise HTTPException(409, "Only active price lists can be paused.")
    now = datetime.now(UTC)
    await repository.update_config(
        tenant_id=tenant_id,
        actor_id=actor_id,
        price_list_id=price_list_id,
        values={
            "status": "paused",
            "schedule_revision": int(row["schedule_revision"]) + 1,
            "next_sync_at": None,
        },
    )
    await build_scheduled_job_repository(uow.session).cancel_matching(
        tenant_id=tenant_id,
        job_type="price_list.sync",
        payload_contains={"price_list_id": str(price_list_id)},
        canceled_at=now,
    )
    return {"status": "paused"}


@router.post(
    "/{price_list_id}/resume",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def resume_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    repository = SqlAlchemyPriceListRepository(uow.session)
    row = await repository.get(tenant_id, price_list_id)
    if row is None:
        raise HTTPException(404, "Price list not found.")
    if row["status"] != "paused":
        raise HTTPException(409, "Only paused price lists can be resumed.")
    revision = int(row["schedule_revision"]) + 1
    run_at = datetime.now(UTC)
    await repository.update_config(
        tenant_id=tenant_id,
        actor_id=actor_id,
        price_list_id=price_list_id,
        values={"status": "active", "schedule_revision": revision},
    )
    job_id = uuid6.uuid7()
    await build_scheduled_job_repository(uow.session).schedule(
        _job(
            job_id=job_id,
            tenant_id=tenant_id,
            price_list_id=price_list_id,
            revision=revision,
            run_at=run_at,
            trigger="cron",
        )
    )
    return {"status": "active", "job_id": job_id}


@router.post("/{price_list_id}/archive", dependencies=[Depends(require_csrf)])
async def archive_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    repository = SqlAlchemyPriceListRepository(uow.session)
    row = await repository.get(tenant_id, price_list_id)
    if row is None:
        raise HTTPException(404, "Price list not found.")
    if row["status"] == "archived":
        raise HTTPException(409, "Price list is already archived.")
    now = datetime.now(UTC)
    await repository.update_config(
        tenant_id=tenant_id,
        actor_id=actor_id,
        price_list_id=price_list_id,
        values={
            "status": "archived",
            "archived_at": now,
            "next_sync_at": None,
            "schedule_revision": int(row["schedule_revision"]) + 1,
        },
    )
    canceled = await build_scheduled_job_repository(uow.session).cancel_matching(
        tenant_id=tenant_id,
        job_type="price_list.sync",
        payload_contains={"price_list_id": str(price_list_id)},
        canceled_at=now,
    )
    return {"status": "archived", "canceled_jobs": canceled}


@router.post("/{price_list_id}/restore", dependencies=[Depends(require_csrf)])
async def restore_price_list(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, actor_id = _ids(context)
    repository = SqlAlchemyPriceListRepository(uow.session)
    row = await repository.get(tenant_id, price_list_id)
    if row is None:
        raise HTTPException(404, "Price list not found.")
    if row["status"] != "archived":
        raise HTTPException(409, "Only archived price lists can be restored.")
    await repository.update_config(
        tenant_id=tenant_id,
        actor_id=actor_id,
        price_list_id=price_list_id,
        values={
            "status": "paused",
            "archived_at": None,
            "next_sync_at": None,
            "schedule_revision": int(row["schedule_revision"]) + 1,
        },
    )
    return {"status": "paused"}


@router.delete(
    "/{price_list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_price_list(
    price_list_id: UUID,
    payload: DeletePriceListRequest,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, _ = _ids(context)
    repository = SqlAlchemyPriceListRepository(uow.session)
    row = await repository.get(tenant_id, price_list_id)
    if row is None:
        raise HTTPException(404, "Price list not found.")
    if row["status"] != "archived":
        raise HTTPException(409, "Archive the price list before deleting it.")
    if payload.confirmation_title != row["title"]:
        raise HTTPException(422, "Confirmation title does not match.")
    await build_scheduled_job_repository(uow.session).delete_matching(
        tenant_id=tenant_id,
        job_type="price_list.sync",
        payload_contains={"price_list_id": str(price_list_id)},
    )
    await repository.delete(tenant_id=tenant_id, price_list_id=price_list_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{price_list_id}/runs")
async def list_runs(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
):
    tenant_id, _ = _ids(context)
    return {
        "items": await SqlAlchemyPriceListRepository(uow.session).list_runs(
            tenant_id, price_list_id
        )
    }


async def _offers_response(
    repository: SqlAlchemyPriceListRepository,
    tenant_id: UUID,
    *,
    price_list_ids: list[UUID],
    purchase_price_min: Decimal | None,
    purchase_price_max: Decimal | None,
    recommended_retail_income_min: Decimal | None,
    recommended_retail_income_max: Decimal | None,
    margin_percent_min: Decimal | None,
    margin_percent_max: Decimal | None,
    availability: list[str],
    has_rrp: bool | None,
    q: str | None,
    sort: str,
    direction: str,
    offset: int,
    limit: int,
    include_archived: bool,
):
    items, total = await repository.list_offers(
        tenant_id=tenant_id,
        filters={
            "price_list_ids": price_list_ids,
            "purchase_price_min": purchase_price_min,
            "purchase_price_max": purchase_price_max,
            "recommended_retail_income_min": recommended_retail_income_min,
            "recommended_retail_income_max": recommended_retail_income_max,
            "margin_percent_min": margin_percent_min,
            "margin_percent_max": margin_percent_max,
            "availability": availability,
            "has_rrp": has_rrp,
            "q": q,
        },
        offset=offset,
        limit=limit,
        sort=sort,
        direction=direction,
        include_archived=include_archived,
    )
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/{price_list_id}/offers")
async def list_price_list_offers(
    price_list_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
    q: str | None = None,
    sort: str = "observed_at",
    direction: Literal["asc", "desc"] = "desc",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_archived: bool = False,
):
    tenant_id, _ = _ids(context)
    return await _offers_response(
        SqlAlchemyPriceListRepository(uow.session),
        tenant_id,
        price_list_ids=[price_list_id],
        purchase_price_min=None,
        purchase_price_max=None,
        recommended_retail_income_min=None,
        recommended_retail_income_max=None,
        margin_percent_min=None,
        margin_percent_max=None,
        availability=[],
        has_rrp=None,
        q=q,
        sort=sort,
        direction=direction,
        offset=offset,
        limit=limit,
        include_archived=include_archived,
    )


@offers_router.get("")
async def list_all_offers(
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
    price_list_id: list[UUID] = Query(default=[]),
    purchase_price_min: Decimal | None = None,
    purchase_price_max: Decimal | None = None,
    recommended_retail_income_min: Decimal | None = None,
    recommended_retail_income_max: Decimal | None = None,
    margin_percent_min: Decimal | None = None,
    margin_percent_max: Decimal | None = None,
    availability: list[str] = Query(default=[]),
    has_rrp: bool | None = None,
    q: str | None = Query(default=None, max_length=255),
    sort: str = "observed_at",
    direction: Literal["asc", "desc"] = "desc",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_archived: bool = False,
):
    tenant_id, _ = _ids(context)
    return await _offers_response(
        SqlAlchemyPriceListRepository(uow.session),
        tenant_id,
        price_list_ids=price_list_id,
        purchase_price_min=purchase_price_min,
        purchase_price_max=purchase_price_max,
        recommended_retail_income_min=recommended_retail_income_min,
        recommended_retail_income_max=recommended_retail_income_max,
        margin_percent_min=margin_percent_min,
        margin_percent_max=margin_percent_max,
        availability=availability,
        has_rrp=has_rrp,
        q=q,
        sort=sort,
        direction=direction,
        offset=offset,
        limit=limit,
        include_archived=include_archived,
    )


@offers_router.get("/{offer_id}/history")
async def offer_history(
    offer_id: UUID,
    context: AuthenticatedRequestContextDep,
    uow: UoWDep,
    observed_from: datetime | None = None,
    observed_to: datetime | None = None,
    purchase_price_min: Decimal | None = None,
    purchase_price_max: Decimal | None = None,
    rrp_min: Decimal | None = None,
    rrp_max: Decimal | None = None,
    recommended_retail_income_min: Decimal | None = None,
    recommended_retail_income_max: Decimal | None = None,
    margin_percent_min: Decimal | None = None,
    margin_percent_max: Decimal | None = None,
    quantity_min: int | None = Query(default=None, ge=0),
    quantity_max: int | None = Query(default=None, ge=0),
    availability: list[str] = Query(default=[]),
    change_reason: list[str] = Query(default=[]),
    sort: str = "observed_at",
    direction: Literal["asc", "desc"] = "desc",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    tenant_id, _ = _ids(context)
    items, total = await SqlAlchemyPriceListRepository(uow.session).offer_history(
        tenant_id=tenant_id,
        offer_id=offer_id,
        filters={
            "observed_from": observed_from,
            "observed_to": observed_to,
            "purchase_price_min": purchase_price_min,
            "purchase_price_max": purchase_price_max,
            "rrp_min": rrp_min,
            "rrp_max": rrp_max,
            "recommended_retail_income_min": recommended_retail_income_min,
            "recommended_retail_income_max": recommended_retail_income_max,
            "margin_percent_min": margin_percent_min,
            "margin_percent_max": margin_percent_max,
            "quantity_min": quantity_min,
            "quantity_max": quantity_max,
            "availability": availability,
            "change_reason": change_reason,
        },
        offset=offset,
        limit=limit,
        sort=sort,
        direction=direction,
    )
    return {"items": items, "total": total, "offset": offset, "limit": limit}

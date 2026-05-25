from __future__ import annotations

from datetime import datetime
from uuid import UUID

import uuid6

from src.modules.shared.domain.events import IntegrationEvent

CRM_CONTACT_CREATED = "crm.contact.created.v1"
CRM_CONTACT_UPDATED = "crm.contact.updated.v1"
CRM_CONTACT_DELETED = "crm.contact.deleted.v1"


def contact_created_event(
    *,
    tenant_id: UUID,
    contact_id: UUID,
    occurred_at: datetime,
    actor_id: UUID | None = None,
    payload: dict,
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id=uuid6.uuid7(),
        tenant_id=tenant_id,
        event_type=CRM_CONTACT_CREATED,
        event_version=1,
        aggregate_type="crm.contact",
        aggregate_id=contact_id,
        payload={
            "contact_id": str(contact_id),
            "actor_id": str(actor_id) if actor_id else None,
            "data": payload,
        },
        occurred_at=occurred_at,
    )


def contact_updated_event(
    *,
    tenant_id: UUID,
    contact_id: UUID,
    occurred_at: datetime,
    actor_id: UUID | None = None,
    changed_fields: list[str],
    before: dict | None = None,
    after: dict | None = None,
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id=uuid6.uuid7(),
        tenant_id=tenant_id,
        event_type=CRM_CONTACT_UPDATED,
        event_version=1,
        aggregate_type="crm.contact",
        aggregate_id=contact_id,
        payload={
            "contact_id": str(contact_id),
            "actor_id": str(actor_id) if actor_id else None,
            "changed_fields": changed_fields,
            "before": before or {},
            "after": after or {},
        },
        occurred_at=occurred_at,
    )


def contact_deleted_event(
    *,
    tenant_id: UUID,
    contact_id: UUID,
    occurred_at: datetime,
    actor_id: UUID | None = None,
    reason: str | None = None,
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id=uuid6.uuid7(),
        tenant_id=tenant_id,
        event_type=CRM_CONTACT_DELETED,
        event_version=1,
        aggregate_type="crm.contact",
        aggregate_id=contact_id,
        payload={
            "contact_id": str(contact_id),
            "actor_id": str(actor_id) if actor_id else None,
            "reason": reason,
        },
        occurred_at=occurred_at,
    )


__all__ = [
    "CRM_CONTACT_CREATED",
    "CRM_CONTACT_DELETED",
    "CRM_CONTACT_UPDATED",
    "contact_created_event",
    "contact_deleted_event",
    "contact_updated_event",
]

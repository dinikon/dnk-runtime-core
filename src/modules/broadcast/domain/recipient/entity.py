from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.shared import EntityIdVO
from src.modules.broadcast.domain.recipient.enum import BroadcastRecipientStatus


@dataclass(slots=True)
class BroadcastRecipientEntity:
    id: EntityIdVO
    tenant_id: EntityIdVO
    broadcast_id: EntityIdVO

    row_number: int

    recipient_identifier_type: str
    recipient_raw_value: str
    recipient_normalized_value: str | None
    recipient_hash: str | None

    variables: dict[str, Any]
    recipient_snapshot: dict[str, Any]

    status: BroadcastRecipientStatus
    validation_errors: list[dict[str, Any]]

    dedupe_key: str | None
    duplicate_of_recipient_id: EntityIdVO | None

    scheduled_at: datetime | None
    processing_started_at: datetime | None
    processing_lock_until: datetime | None
    processing_token: str | None

    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None

    communication_request_id: EntityIdVO | None
    outbound_message_id: EntityIdVO | None

    attempt_count: int
    last_error: str | None

    created_at: datetime
    updated_at: datetime

    @classmethod
    def ready(
        cls,
        *,
        id_: EntityIdVO,
        tenant_id: EntityIdVO,
        broadcast_id: EntityIdVO,
        row_number: int,
        recipient_identifier_type: str,
        recipient_raw_value: str,
        recipient_normalized_value: str,
        recipient_hash: str,
        variables: dict[str, Any],
        recipient_snapshot: dict[str, Any],
        dedupe_key: str,
        now: datetime,
    ) -> Self:
        return cls(
            id=id_,
            tenant_id=tenant_id,
            broadcast_id=broadcast_id,
            row_number=row_number,
            recipient_identifier_type=recipient_identifier_type,
            recipient_raw_value=recipient_raw_value,
            recipient_normalized_value=recipient_normalized_value,
            recipient_hash=recipient_hash,
            variables=variables,
            recipient_snapshot=recipient_snapshot,
            status=BroadcastRecipientStatus.READY,
            validation_errors=[],
            dedupe_key=dedupe_key,
            duplicate_of_recipient_id=None,
            scheduled_at=None,
            processing_started_at=None,
            processing_lock_until=None,
            processing_token=None,
            sent_at=None,
            delivered_at=None,
            failed_at=None,
            communication_request_id=None,
            outbound_message_id=None,
            attempt_count=0,
            last_error=None,
            created_at=now,
            updated_at=now,
        )

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryRow,
)


class ContentDeliveryTargetResponse(BaseModel):
    """Публичные поля цели без запроса, токенов и credentials."""

    publication_id: UUID
    external_id: str
    role: str
    publication_kind: str
    revision: int
    requested_generation: int
    sending_generation: int | None
    applied_generation: int | None
    status: str
    confirmed_fields: tuple[str, ...]
    error_code: str | None
    updated_at: datetime
    completed_at: datetime | None
    content_fingerprint: str
    recovery_required: bool

    @classmethod
    def from_row(cls, value: ContentDeliveryRow) -> "ContentDeliveryTargetResponse":
        """Явно выбирает поля сценария вместо автоматической сериализации агрегата."""
        return cls(
            publication_id=value.publication_id,
            external_id=value.external_id,
            role=value.role,
            publication_kind=value.publication_kind,
            revision=value.revision,
            requested_generation=value.requested_generation,
            sending_generation=value.sending_generation,
            applied_generation=value.applied_generation,
            status=value.status,
            confirmed_fields=value.confirmed_fields,
            error_code=value.error_code,
            updated_at=value.updated_at,
            completed_at=value.completed_at,
            content_fingerprint=value.content_fingerprint,
            recovery_required=value.recovery_required,
        )

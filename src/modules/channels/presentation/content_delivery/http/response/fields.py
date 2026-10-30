from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryRow,
)


class ContentDeliveryFieldIssueResponse(BaseModel):
    """Имя неподтверждённого поля и безопасная причина расхождения."""

    field: str
    code: str


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
    field_issues: tuple[ContentDeliveryFieldIssueResponse, ...]
    initial_error_code: str | None
    last_success_at: datetime | None
    applied_content_fingerprint: str | None

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
            field_issues=tuple(
                ContentDeliveryFieldIssueResponse(field=v.field, code=v.code)
                for v in value.field_issues
            ),
            initial_error_code=value.initial_error_code,
            last_success_at=value.last_success_at,
            applied_content_fingerprint=value.applied_content_fingerprint,
        )

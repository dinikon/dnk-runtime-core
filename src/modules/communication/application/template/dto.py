from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TemplateVersionDTO:
    template_version_id: UUID
    template_id: UUID
    version_no: int
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: str
    created_at: datetime
    activated_at: datetime | None


@dataclass(frozen=True, slots=True)
class MessageTemplateDTO:
    template_id: UUID
    tenant_id: UUID
    template_code: str
    name: str
    description: str | None
    provider_connector_id: UUID
    provider_message_type_id: UUID
    channel_code: str
    message_class: str
    status: str
    created_at: datetime
    updated_at: datetime
    active_version_id: UUID | None = None
    active_version_no: int | None = None


__all__ = [
    "MessageTemplateDTO",
    "TemplateVersionDTO",
]

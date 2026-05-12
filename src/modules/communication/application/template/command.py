from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateMessageTemplateCommand:
    tenant_id: UUID
    template_code: str
    name: str
    description: str | None
    provider_connector_id: UUID
    provider_message_type_id: UUID
    channel_code: str
    message_class: str


@dataclass(frozen=True, slots=True)
class CreateTemplateVersionCommand:
    tenant_id: UUID
    template_id: UUID
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActivateTemplateVersionCommand:
    tenant_id: UUID
    template_id: UUID
    template_version_id: UUID


__all__ = [
    "ActivateTemplateVersionCommand",
    "CreateMessageTemplateCommand",
    "CreateTemplateVersionCommand",
]

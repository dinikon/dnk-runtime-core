from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TemplateVersionDTO:
    """DTO template version для application/presentation boundary."""

    template_version_id: UUID
    template_id: UUID
    version: datetime
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: str
    created_at: datetime
    activated_at: datetime | None


__all__ = ["TemplateVersionDTO"]

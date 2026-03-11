from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class ObjectMetadataEntity:
    id: UUID
    tenant_id: UUID
    source_id: UUID
    name_singular: str
    name_plural: str
    label_singular: str
    label_plural: str
    description: str
    icon: str
    is_custom: str
    is_remote: str
    is_active: str
    is_system: str
    is_ui_read_only: str
    is_audit_logged: str
    is_searchable: str
    duplicate_criteria: str
    shortcut: str | None
    isLabelSyncedWithName: bool
    label_identifier_field_metadata_id: UUID | None
    created_at: datetime
    updated_at: datetime


__all__ = ["ObjectMetadataEntity"]

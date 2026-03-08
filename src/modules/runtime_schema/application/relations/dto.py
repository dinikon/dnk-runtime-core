from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateRelationCommandDTO:
    tenant_id: UUID
    schema: str
    kind: str
    source_object_metadata_id: UUID
    source_field_metadata_id: UUID | None
    target_object_metadata_id: UUID
    target_field_metadata_id: UUID | None = None
    reverse_name_field: str | None = None
    reverse_label: str | None = None
    on_delete: str = "restrict"
    is_required: bool = False
    is_system: bool = False
    junction_table_name: str | None = None


@dataclass(frozen=True, slots=True)
class CreateRelationResultDTO:
    relation_id: UUID
    kind: str
    reverse_kind: str
    junction_table_name: str | None


@dataclass(frozen=True, slots=True)
class DeleteRelationCommandDTO:
    relation_id: UUID
    schema: str


@dataclass(frozen=True, slots=True)
class DeleteRelationResultDTO:
    ok: bool

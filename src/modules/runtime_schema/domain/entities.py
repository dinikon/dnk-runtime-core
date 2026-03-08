from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.modules.shared.domain.errors import ValidationError
from src.modules.runtime_schema.domain.errors import (
    InvalidRequiredRelationOnDeleteError,
    RelationJunctionTableRequiredError,
    RelationOwnerFieldRequiredError,
    RelationTargetFieldRequiredError,
)
from src.modules.runtime_schema.domain.value_objects.field_type import (
    RuntimeSchemaFieldType,
)
from src.modules.runtime_schema.domain.value_objects.relation_kind import (
    RuntimeSchemaRelationKind,
)
from src.modules.runtime_schema.domain.value_objects.relation_on_delete import (
    RuntimeSchemaRelationOnDelete,
)

JsonValue = object


@dataclass(slots=True)
class ObjectMetadata:
    id: UUID
    tenant_id: UUID
    data_source_id: UUID
    table_name: str
    name_singular: str
    name_plural: str
    label_singular: str
    label_plural: str
    description: str | None
    icon: str | None
    is_custom: bool
    is_remote: bool
    is_active: bool
    is_system: bool
    is_ui_read_only: bool
    is_audit_logged: bool
    is_searchable: bool
    duplicate_criteria: JsonValue | None
    shortcut: str | None
    label_identifier_field_metadata_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_system(
        cls,
        *,
        tenant_id: UUID,
        data_source_id: UUID,
        table_name: str,
        name_singular: str,
        name_plural: str,
        label_singular: str,
        label_plural: str,
        description: str | None = None,
        icon: str | None = None,
        is_ui_read_only: bool = False,
        is_audit_logged: bool = False,
        is_searchable: bool = True,
        duplicate_criteria: JsonValue | None = None,
        shortcut: str | None = None,
    ) -> "ObjectMetadata":
        normalized_table_name = table_name.strip().lower()
        normalized_name_singular = name_singular.strip().lower()
        normalized_name_plural = name_plural.strip().lower()
        normalized_label_singular = label_singular.strip()
        normalized_label_plural = label_plural.strip()
        if not normalized_table_name:
            raise ValidationError("Object metadata table_name must not be empty.")
        if not normalized_name_singular:
            raise ValidationError("Object metadata name_singular must not be empty.")
        if not normalized_name_plural:
            raise ValidationError("Object metadata name_plural must not be empty.")
        if not normalized_label_singular:
            raise ValidationError("Object metadata label_singular must not be empty.")
        if not normalized_label_plural:
            raise ValidationError("Object metadata label_plural must not be empty.")

        normalized_description = description.strip() if description else None
        normalized_icon = icon.strip() if icon else None
        normalized_shortcut = shortcut.strip() if shortcut else None
        now = datetime.now(UTC)
        return cls(
            id=uuid6.uuid7(),
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            table_name=normalized_table_name,
            name_singular=normalized_name_singular,
            name_plural=normalized_name_plural,
            label_singular=normalized_label_singular,
            label_plural=normalized_label_plural,
            description=normalized_description,
            icon=normalized_icon,
            is_custom=False,
            is_remote=False,
            is_active=True,
            is_system=True,
            is_ui_read_only=is_ui_read_only,
            is_audit_logged=is_audit_logged,
            is_searchable=is_searchable,
            duplicate_criteria=duplicate_criteria,
            shortcut=normalized_shortcut,
            label_identifier_field_metadata_id=None,
            created_at=now,
            updated_at=now,
        )

    def bind_label_identifier_field(self, field_metadata_id: UUID) -> None:
        self.label_identifier_field_metadata_id = field_metadata_id
        self.updated_at = datetime.now(UTC)


@dataclass(slots=True)
class FieldMetadata:
    id: UUID
    tenant_id: UUID
    object_metadata_id: UUID
    field_type: RuntimeSchemaFieldType
    name_field: str
    label: str
    default_value: JsonValue | None
    description: str | None
    icon: str | None
    options: JsonValue | None
    settings: JsonValue | None
    is_custom: bool
    is_active: bool
    is_system: bool
    is_ui_read_only: bool
    is_nullable: bool
    is_unique: bool
    relation_target_field_metadata_id: UUID | None
    relation_target_object_metadata_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_system(
        cls,
        *,
        tenant_id: UUID,
        object_metadata_id: UUID,
        field_type: RuntimeSchemaFieldType,
        name_field: str,
        label: str,
        default_value: JsonValue | None = None,
        description: str | None = None,
        icon: str | None = None,
        options: JsonValue | None = None,
        settings: JsonValue | None = None,
        is_ui_read_only: bool = False,
        is_nullable: bool = True,
        is_unique: bool = False,
    ) -> "FieldMetadata":
        normalized_name_field = name_field.strip().lower()
        normalized_label = label.strip()
        if not normalized_name_field:
            raise ValidationError("Field metadata name_field must not be empty.")
        if not normalized_label:
            raise ValidationError("Field metadata label must not be empty.")

        normalized_description = description.strip() if description else None
        normalized_icon = icon.strip() if icon else None
        now = datetime.now(UTC)
        return cls(
            id=uuid6.uuid7(),
            tenant_id=tenant_id,
            object_metadata_id=object_metadata_id,
            field_type=field_type,
            name_field=normalized_name_field,
            label=normalized_label,
            default_value=default_value,
            description=normalized_description,
            icon=normalized_icon,
            options=options,
            settings=settings,
            is_custom=False,
            is_active=True,
            is_system=True,
            is_ui_read_only=is_ui_read_only,
            is_nullable=is_nullable,
            is_unique=is_unique,
            relation_target_field_metadata_id=None,
            relation_target_object_metadata_id=None,
            created_at=now,
            updated_at=now,
        )

    def bind_relation(
        self,
        relation_target_object_metadata_id: UUID,
        relation_target_field_metadata_id: UUID,
    ) -> None:
        self.relation_target_object_metadata_id = relation_target_object_metadata_id
        self.relation_target_field_metadata_id = relation_target_field_metadata_id
        self.updated_at = datetime.now(UTC)

    def unbind_relation(self) -> None:
        self.relation_target_object_metadata_id = None
        self.relation_target_field_metadata_id = None
        self.updated_at = datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SystemFieldDefinition:
    name_field: str
    column_name: str
    field_type: RuntimeSchemaFieldType
    label: str
    is_nullable: bool
    is_unique: bool = False
    is_ui_read_only: bool = False
    default_value: JsonValue | None = None
    description: str | None = None
    icon: str | None = None
    options: JsonValue | None = None
    settings: JsonValue | None = None
    relation_kind: RuntimeSchemaRelationKind | None = None
    relation_target_object_name_singular: str | None = None
    relation_target_field_name: str | None = None
    reverse_name_field: str | None = None
    reverse_label: str | None = None
    relation_on_delete: RuntimeSchemaRelationOnDelete = (
        RuntimeSchemaRelationOnDelete.RESTRICT
    )
    is_primary_key: bool = False
    default_sql: str | None = None


@dataclass(frozen=True, slots=True)
class SystemObjectDefinition:
    name_singular: str
    name_plural: str
    label_singular: str
    label_plural: str
    table_name: str
    label_identifier_field_name: str
    fields: Sequence[SystemFieldDefinition]
    description: str | None = None
    icon: str | None = None
    is_ui_read_only: bool = False
    is_audit_logged: bool = False
    is_searchable: bool = True
    duplicate_criteria: JsonValue | None = None
    shortcut: str | None = None


@dataclass(slots=True)
class RelationMetadata:
    id: UUID
    tenant_id: UUID
    source_object_metadata_id: UUID
    source_field_metadata_id: UUID | None
    target_object_metadata_id: UUID
    target_field_metadata_id: UUID | None
    kind: RuntimeSchemaRelationKind
    reverse_name_field: str | None
    reverse_label: str | None
    junction_table_name: str | None
    on_delete: RuntimeSchemaRelationOnDelete
    is_required: bool
    is_custom: bool
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @property
    def reverse_kind(self) -> RuntimeSchemaRelationKind:
        if self.kind == RuntimeSchemaRelationKind.MANY_TO_ONE:
            return RuntimeSchemaRelationKind.ONE_TO_MANY
        return self.kind

    @property
    def is_owner_relation(self) -> bool:
        return self.kind in {
            RuntimeSchemaRelationKind.MANY_TO_ONE,
            RuntimeSchemaRelationKind.ONE_TO_ONE,
        }

    @classmethod
    def create_many_to_one(
        cls,
        *,
        tenant_id: UUID,
        source_object_metadata_id: UUID,
        source_field_metadata_id: UUID,
        target_object_metadata_id: UUID,
        target_field_metadata_id: UUID,
        reverse_name_field: str | None = None,
        reverse_label: str | None = None,
        on_delete: RuntimeSchemaRelationOnDelete = RuntimeSchemaRelationOnDelete.RESTRICT,
        is_required: bool = False,
        is_system: bool = False,
    ) -> "RelationMetadata":
        return cls._create(
            tenant_id=tenant_id,
            source_object_metadata_id=source_object_metadata_id,
            source_field_metadata_id=source_field_metadata_id,
            target_object_metadata_id=target_object_metadata_id,
            target_field_metadata_id=target_field_metadata_id,
            kind=RuntimeSchemaRelationKind.MANY_TO_ONE,
            reverse_name_field=reverse_name_field,
            reverse_label=reverse_label,
            junction_table_name=None,
            on_delete=on_delete,
            is_required=is_required,
            is_system=is_system,
        )

    @classmethod
    def create_one_to_one(
        cls,
        *,
        tenant_id: UUID,
        source_object_metadata_id: UUID,
        source_field_metadata_id: UUID,
        target_object_metadata_id: UUID,
        target_field_metadata_id: UUID,
        reverse_name_field: str | None = None,
        reverse_label: str | None = None,
        on_delete: RuntimeSchemaRelationOnDelete = RuntimeSchemaRelationOnDelete.RESTRICT,
        is_required: bool = False,
        is_system: bool = False,
    ) -> "RelationMetadata":
        return cls._create(
            tenant_id=tenant_id,
            source_object_metadata_id=source_object_metadata_id,
            source_field_metadata_id=source_field_metadata_id,
            target_object_metadata_id=target_object_metadata_id,
            target_field_metadata_id=target_field_metadata_id,
            kind=RuntimeSchemaRelationKind.ONE_TO_ONE,
            reverse_name_field=reverse_name_field,
            reverse_label=reverse_label,
            junction_table_name=None,
            on_delete=on_delete,
            is_required=is_required,
            is_system=is_system,
        )

    @classmethod
    def create_many_to_many(
        cls,
        *,
        tenant_id: UUID,
        source_object_metadata_id: UUID,
        target_object_metadata_id: UUID,
        junction_table_name: str,
        reverse_name_field: str | None = None,
        reverse_label: str | None = None,
        is_system: bool = False,
    ) -> "RelationMetadata":
        return cls._create(
            tenant_id=tenant_id,
            source_object_metadata_id=source_object_metadata_id,
            source_field_metadata_id=None,
            target_object_metadata_id=target_object_metadata_id,
            target_field_metadata_id=None,
            kind=RuntimeSchemaRelationKind.MANY_TO_MANY,
            reverse_name_field=reverse_name_field,
            reverse_label=reverse_label,
            junction_table_name=junction_table_name,
            on_delete=RuntimeSchemaRelationOnDelete.CASCADE,
            is_required=False,
            is_system=is_system,
        )

    @classmethod
    def _create(
        cls,
        *,
        tenant_id: UUID,
        source_object_metadata_id: UUID,
        source_field_metadata_id: UUID | None,
        target_object_metadata_id: UUID,
        target_field_metadata_id: UUID | None,
        kind: RuntimeSchemaRelationKind,
        reverse_name_field: str | None,
        reverse_label: str | None,
        junction_table_name: str | None,
        on_delete: RuntimeSchemaRelationOnDelete,
        is_required: bool,
        is_system: bool,
    ) -> "RelationMetadata":
        normalized_reverse_name_field = (
            reverse_name_field.strip().lower() if reverse_name_field else None
        )
        normalized_reverse_label = reverse_label.strip() if reverse_label else None
        normalized_junction_table_name = (
            junction_table_name.strip().lower() if junction_table_name else None
        )
        if kind in {
            RuntimeSchemaRelationKind.MANY_TO_ONE,
            RuntimeSchemaRelationKind.ONE_TO_ONE,
        }:
            if source_field_metadata_id is None:
                raise RelationOwnerFieldRequiredError()
            if target_field_metadata_id is None:
                raise RelationTargetFieldRequiredError()
            if is_required and on_delete == RuntimeSchemaRelationOnDelete.SET_NULL:
                raise InvalidRequiredRelationOnDeleteError(on_delete.value)
        if kind == RuntimeSchemaRelationKind.MANY_TO_MANY:
            if not normalized_junction_table_name:
                raise RelationJunctionTableRequiredError()

        now = datetime.now(UTC)
        return cls(
            id=uuid6.uuid7(),
            tenant_id=tenant_id,
            source_object_metadata_id=source_object_metadata_id,
            source_field_metadata_id=source_field_metadata_id,
            target_object_metadata_id=target_object_metadata_id,
            target_field_metadata_id=target_field_metadata_id,
            kind=kind,
            reverse_name_field=normalized_reverse_name_field,
            reverse_label=normalized_reverse_label,
            junction_table_name=normalized_junction_table_name,
            on_delete=on_delete,
            is_required=is_required,
            is_custom=not is_system,
            is_system=is_system,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.now(UTC)

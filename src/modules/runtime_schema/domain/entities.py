from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from re import Pattern, compile as re_compile
from uuid import UUID

import uuid6

from src.modules.runtime_schema.domain.errors import (
    InvalidDataSourceSchemaError,
    InvalidDataSourceTypeError,
    InvalidFieldNameError,
    InvalidFieldTypeError,
    InvalidObjectOwnershipKindError,
    ObjectOwnershipKindImmutableError,
)
from src.modules.runtime_schema.domain.value_objects import (
    FIELD_NAME_MAX_LENGTH,
    DataSourceType,
    FieldType,
    ObjectOwnershipKind,
)

_FIELD_NAME_PATTERN: Pattern[str] = re_compile(
    rf"^[a-z][a-z0-9_]{{0,{FIELD_NAME_MAX_LENGTH - 1}}}$"
)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _parse_data_source_type(value: DataSourceType | str) -> DataSourceType:
    try:
        parsed = value if isinstance(value, DataSourceType) else DataSourceType(value)
    except ValueError as exc:
        raise InvalidDataSourceTypeError(str(value)) from exc

    if parsed is not DataSourceType.POSTGRESQL:
        raise InvalidDataSourceTypeError(str(value))

    return parsed


def _parse_ownership_kind(
    value: ObjectOwnershipKind | str,
) -> ObjectOwnershipKind:
    try:
        return (
            value
            if isinstance(value, ObjectOwnershipKind)
            else ObjectOwnershipKind(value)
        )
    except ValueError as exc:
        raise InvalidObjectOwnershipKindError(str(value)) from exc


def _parse_field_type(value: FieldType | str) -> FieldType:
    try:
        return value if isinstance(value, FieldType) else FieldType(value)
    except ValueError as exc:
        raise InvalidFieldTypeError(str(value)) from exc


def _validate_schema_uuid(value: str) -> str:
    normalized = value.strip()
    try:
        UUID(normalized)
    except ValueError as exc:
        raise InvalidDataSourceSchemaError(value) from exc
    return normalized


def _validate_field_name(value: str) -> str:
    normalized = value.strip()
    if not _FIELD_NAME_PATTERN.fullmatch(normalized):
        raise InvalidFieldNameError(value)
    return normalized


@dataclass(frozen=True, slots=True)
class DataSource:
    id: UUID
    created_at: datetime
    updated_at: datetime
    tenant_id: UUID
    type: DataSourceType
    schema: str
    url: str

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        source_type: DataSourceType | str = DataSourceType.POSTGRESQL,
        schema: str | None = None,
        url: str = "",
        now: datetime | None = None,
    ) -> "DataSource":
        created_at = now or _now_utc()
        resolved_schema = _validate_schema_uuid(schema or str(uuid6.uuid7()))
        resolved_type = _parse_data_source_type(source_type)

        return cls(
            id=uuid6.uuid7(),
            created_at=created_at,
            updated_at=created_at,
            tenant_id=tenant_id,
            type=resolved_type,
            schema=resolved_schema,
            url=url.strip(),
        )


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    id: UUID
    created_at: datetime
    updated_at: datetime
    tenant_id: UUID
    data_source_id: UUID
    name_singular: str
    name_plural: str
    label_singular: str
    label_plural: str
    description: str | None
    icon: str | None
    is_system: bool
    duplicate_criteria: str | None
    shortcut: str | None
    ownership_kind: ObjectOwnershipKind
    allows_custom_fields: bool

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        data_source_id: UUID,
        name_singular: str,
        name_plural: str,
        label_singular: str,
        label_plural: str,
        ownership_kind: ObjectOwnershipKind | str,
        allows_custom_fields: bool,
        is_system: bool = False,
        description: str | None = None,
        icon: str | None = None,
        duplicate_criteria: str | None = None,
        shortcut: str | None = None,
        now: datetime | None = None,
    ) -> "ObjectMetadata":
        created_at = now or _now_utc()
        return cls(
            id=uuid6.uuid7(),
            created_at=created_at,
            updated_at=created_at,
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            name_singular=name_singular.strip(),
            name_plural=name_plural.strip(),
            label_singular=label_singular.strip(),
            label_plural=label_plural.strip(),
            description=description,
            icon=icon,
            is_system=is_system,
            duplicate_criteria=duplicate_criteria,
            shortcut=shortcut,
            ownership_kind=_parse_ownership_kind(ownership_kind),
            allows_custom_fields=allows_custom_fields,
        )

    def assert_ownership_kind_immutable(
        self,
        next_ownership_kind: ObjectOwnershipKind | str,
    ) -> None:
        if _parse_ownership_kind(next_ownership_kind) != self.ownership_kind:
            raise ObjectOwnershipKindImmutableError()


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    id: UUID
    created_at: datetime
    updated_at: datetime
    object_metadata_id: UUID
    type: FieldType
    name: str
    label: str
    default_value: object | None
    description: str | None
    icon: str | None
    options: tuple[str, ...]
    settings: dict[str, object]
    is_active: bool
    is_nullable: bool
    is_unique: bool
    workspace_id: UUID | None

    @classmethod
    def create(
        cls,
        *,
        object_metadata_id: UUID,
        field_type: FieldType | str,
        name: str,
        label: str,
        default_value: object | None = None,
        description: str | None = None,
        icon: str | None = None,
        options: tuple[str, ...] | list[str] | None = None,
        settings: dict[str, object] | None = None,
        is_active: bool = True,
        is_nullable: bool = True,
        is_unique: bool = False,
        workspace_id: UUID | None = None,
        now: datetime | None = None,
    ) -> "FieldMetadata":
        created_at = now or _now_utc()

        return cls(
            id=uuid6.uuid7(),
            created_at=created_at,
            updated_at=created_at,
            object_metadata_id=object_metadata_id,
            type=_parse_field_type(field_type),
            name=_validate_field_name(name),
            label=label.strip(),
            default_value=default_value,
            description=description,
            icon=icon,
            options=tuple(options or ()),
            settings=dict(settings or {}),
            is_active=is_active,
            is_nullable=is_nullable,
            is_unique=is_unique,
            workspace_id=workspace_id,
        )

    def deactivate(self, *, now: datetime | None = None) -> "FieldMetadata":
        if not self.is_active:
            return self

        return replace(self, is_active=False, updated_at=now or _now_utc())


__all__ = [
    "DataSource",
    "FieldMetadata",
    "ObjectMetadata",
]

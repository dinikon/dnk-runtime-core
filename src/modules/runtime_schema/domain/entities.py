from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID

import uuid6

from src.modules.runtime_schema.domain.errors import ObjectOwnershipKindImmutableError
from src.modules.runtime_schema.domain.value_objects import (
    DataSourceSchemaVO,
    DataSourceType,
    FieldNameVO,
    FieldType,
    ObjectOwnershipKind,
    normalize_optional_text,
    normalize_required_text,
)


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class DataSource:
    id: UUID
    created_at: datetime
    updated_at: datetime
    tenant_id: UUID
    type: DataSourceType
    schema: str
    url: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", DataSourceType.parse(self.type))
        object.__setattr__(self, "schema", DataSourceSchemaVO(self.schema).value)
        object.__setattr__(self, "url", normalize_required_text(self.url))

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
        resolved_schema = schema if schema is not None else str(uuid6.uuid7())

        return cls(
            id=uuid6.uuid7(),
            created_at=created_at,
            updated_at=created_at,
            tenant_id=tenant_id,
            type=source_type,
            schema=resolved_schema,
            url=url,
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

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name_singular",
            normalize_required_text(self.name_singular),
        )
        object.__setattr__(
            self, "name_plural", normalize_required_text(self.name_plural)
        )
        object.__setattr__(
            self,
            "label_singular",
            normalize_required_text(self.label_singular),
        )
        object.__setattr__(
            self, "label_plural", normalize_required_text(self.label_plural)
        )
        object.__setattr__(
            self, "description", normalize_optional_text(self.description)
        )
        object.__setattr__(self, "icon", normalize_optional_text(self.icon))
        object.__setattr__(
            self,
            "duplicate_criteria",
            normalize_optional_text(self.duplicate_criteria),
        )
        object.__setattr__(self, "shortcut", normalize_optional_text(self.shortcut))
        object.__setattr__(
            self,
            "ownership_kind",
            ObjectOwnershipKind.parse(self.ownership_kind),
        )

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
            name_singular=name_singular,
            name_plural=name_plural,
            label_singular=label_singular,
            label_plural=label_plural,
            description=description,
            icon=icon,
            is_system=is_system,
            duplicate_criteria=duplicate_criteria,
            shortcut=shortcut,
            ownership_kind=ownership_kind,
            allows_custom_fields=allows_custom_fields,
        )

    def assert_ownership_kind_immutable(
        self,
        next_ownership_kind: ObjectOwnershipKind | str,
    ) -> None:
        if ObjectOwnershipKind.parse(next_ownership_kind) != self.ownership_kind:
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
    tenant_id: UUID

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", FieldType.parse(self.type))
        object.__setattr__(self, "name", FieldNameVO(self.name).value)
        object.__setattr__(self, "label", normalize_required_text(self.label))
        object.__setattr__(
            self, "description", normalize_optional_text(self.description)
        )
        object.__setattr__(self, "icon", normalize_optional_text(self.icon))
        object.__setattr__(
            self,
            "options",
            tuple(normalize_required_text(option) for option in self.options),
        )
        object.__setattr__(self, "settings", dict(self.settings))

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
        tenant_id: UUID,
        now: datetime | None = None,
    ) -> "FieldMetadata":
        created_at = now or _now_utc()

        return cls(
            id=uuid6.uuid7(),
            created_at=created_at,
            updated_at=created_at,
            object_metadata_id=object_metadata_id,
            type=field_type,
            name=name,
            label=label,
            default_value=default_value,
            description=description,
            icon=icon,
            options=tuple(options or ()),
            settings=dict(settings or {}),
            is_active=is_active,
            is_nullable=is_nullable,
            is_unique=is_unique,
            tenant_id=tenant_id,
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

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class RelationEntity:
    """Доменная сущность relation metadata между runtime-объектами."""

    id: RuntimeRelationIdVO
    created_at: datetime
    updated_at: datetime

    tenant_id: EntityIdVO
    data_source_id: DataSourceIdVO

    name: str
    label: str | None
    relation_type: RelationTypeEnum

    source_object_id: RuntimeObjectIdVO
    target_object_id: RuntimeObjectIdVO

    owning_object_id: RuntimeObjectIdVO | None
    fk_field_id: RuntimeFieldIdVO | None
    referenced_object_id: RuntimeObjectIdVO | None
    referenced_field_id: RuntimeFieldIdVO | None

    source_relation_name: str
    target_relation_name: str

    relation_table_name: str | None
    source_join_column_name: str | None
    target_join_column_name: str | None

    on_delete: str
    is_required: bool
    is_unique: bool
    kind: str
    settings: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        id_: RuntimeRelationIdVO,
        now: datetime,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        name: str,
        relation_type: RelationTypeEnum,
        source_object_id: RuntimeObjectIdVO,
        target_object_id: RuntimeObjectIdVO,
        owning_object_id: RuntimeObjectIdVO | None,
        fk_field_id: RuntimeFieldIdVO | None,
        referenced_object_id: RuntimeObjectIdVO | None,
        referenced_field_id: RuntimeFieldIdVO | None,
        source_relation_name: str,
        target_relation_name: str,
        relation_table_name: str | None,
        source_join_column_name: str | None,
        target_join_column_name: str | None,
        on_delete: str,
        is_required: bool,
        is_unique: bool,
        kind: str,
        settings: dict[str, Any] | None = None,
        label: str | None = None,
    ) -> Self:
        """Создает relation metadata с нормализованными строковыми полями."""
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            name=name.strip(),
            label=label.strip() if label else None,
            relation_type=relation_type,
            source_object_id=source_object_id,
            target_object_id=target_object_id,
            owning_object_id=owning_object_id,
            fk_field_id=fk_field_id,
            referenced_object_id=referenced_object_id,
            referenced_field_id=referenced_field_id,
            source_relation_name=source_relation_name.strip(),
            target_relation_name=target_relation_name.strip(),
            relation_table_name=(
                relation_table_name.strip() if relation_table_name else None
            ),
            source_join_column_name=(
                source_join_column_name.strip() if source_join_column_name else None
            ),
            target_join_column_name=(
                target_join_column_name.strip() if target_join_column_name else None
            ),
            on_delete=on_delete.strip().lower(),
            is_required=is_required,
            is_unique=is_unique,
            kind=kind.strip().lower(),
            settings=dict(settings or {}),
        )

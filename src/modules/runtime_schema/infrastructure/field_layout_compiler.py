from __future__ import annotations

from dataclasses import dataclass

from src.modules.runtime_schema.domain.field.configuration import (
    FullNameFieldSettings,
    RelationFieldSettings,
    StringFieldSettings,
)
from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import FieldTypeVO
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.infrastructure.contracts import (
    FieldLayoutCompilerProtocol,
)
from src.modules.runtime_schema.infrastructure.ddl_models import (
    ColumnSpec,
    IndexSpec,
    SchemaSnapshot,
    TableSpec,
)


@dataclass(slots=True, frozen=True)
class _CompiledColumns:
    columns: tuple[ColumnSpec, ...]
    is_virtual: bool = False


class FieldLayoutCompiler(FieldLayoutCompilerProtocol):
    def compile_layout(
        self,
        *,
        objects: list[ObjectMetadataEntity],
        fields: list[FieldMetadataEntity],
    ) -> SchemaSnapshot:
        object_table_name_by_id: dict[str, str] = {
            str(object_entity.id.value): object_entity.object_name.name_plural
            for object_entity in objects
        }
        fields_by_object: dict[str, list[FieldMetadataEntity]] = {}
        for field in fields:
            fields_by_object.setdefault(str(field.object_metadata_id.value), []).append(
                field
            )

        tables: dict[str, TableSpec] = {}
        for object_entity in objects:
            table_name = object_entity.object_name.name_plural
            object_fields = fields_by_object.get(str(object_entity.id.value), [])

            columns: list[ColumnSpec] = []
            indexes: list[IndexSpec] = []
            for field_entity in object_fields:
                compiled_columns = self._compile_field_columns(
                    field_entity,
                    object_table_name_by_id=object_table_name_by_id,
                )
                if compiled_columns.is_virtual:
                    continue
                columns.extend(compiled_columns.columns)
                for column in compiled_columns.columns:
                    if field_entity.is_unique:
                        indexes.append(
                            IndexSpec(
                                name=self._index_name(
                                    prefix="uq",
                                    table_name=table_name,
                                    column_names=(column.name,),
                                ),
                                columns=(column.name,),
                                unique=True,
                            )
                        )
                    elif field_entity.is_index:
                        indexes.append(
                            IndexSpec(
                                name=self._index_name(
                                    prefix="ix",
                                    table_name=table_name,
                                    column_names=(column.name,),
                                ),
                                columns=(column.name,),
                                unique=False,
                            )
                        )

            self._append_entity_owner_index(
                table_name=table_name,
                columns=columns,
                indexes=indexes,
            )

            if not any(column.name == "id" for column in columns):
                columns.insert(
                    0,
                    ColumnSpec(
                        name="id",
                        sql_type="uuid",
                        nullable=False,
                        is_primary_key=True,
                    ),
                )
            else:
                columns = [
                    ColumnSpec(
                        name=column.name,
                        sql_type=column.sql_type,
                        nullable=column.nullable,
                        is_primary_key=(column.name == "id") or column.is_primary_key,
                        default_sql=column.default_sql,
                        references_table=column.references_table,
                        references_column=column.references_column,
                        on_delete=column.on_delete,
                    )
                    for column in columns
                ]

            tables[table_name] = TableSpec(
                name=table_name,
                columns=tuple(columns),
                indexes=tuple(indexes),
            )
        return SchemaSnapshot(tables=tables)

    def _compile_field_columns(
        self,
        field: FieldMetadataEntity,
        *,
        object_table_name_by_id: dict[str, str] | None = None,
    ) -> _CompiledColumns:
        field_name = field.field_name.value
        nullable = field.is_nullable

        if field.field_type == FieldTypeVO.UUID:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(name=field_name, sql_type="uuid", nullable=nullable),
                )
            )

        if field.field_type in {FieldTypeVO.STRING, FieldTypeVO.TEXT}:
            sql_type = "text"
            if isinstance(field.settings, StringFieldSettings):
                max_length = field.settings.max_length
                if max_length is not None and max_length > 0 and max_length <= 1024:
                    sql_type = f"varchar({max_length})"
            elif field.field_type == FieldTypeVO.STRING:
                sql_type = "varchar(255)"
            return _CompiledColumns(
                columns=(
                    ColumnSpec(name=field_name, sql_type=sql_type, nullable=nullable),
                )
            )

        if field.field_type == FieldTypeVO.INTEGER:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(name=field_name, sql_type="bigint", nullable=nullable),
                )
            )

        if field.field_type == FieldTypeVO.BOOLEAN:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(name=field_name, sql_type="boolean", nullable=nullable),
                )
            )

        if field.field_type == FieldTypeVO.DATE_TIME:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(
                        name=field_name, sql_type="timestamp_tz", nullable=nullable
                    ),
                )
            )

        if field.field_type == FieldTypeVO.JSON:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(name=field_name, sql_type="json", nullable=nullable),
                )
            )

        if field.field_type in {
            FieldTypeVO.ARRAY,
            FieldTypeVO.MULTI_SELECT,
            FieldTypeVO.EMAILS,
            FieldTypeVO.LINKS,
            FieldTypeVO.PHONES,
        }:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(name=field_name, sql_type="json", nullable=nullable),
                )
            )

        if field.field_type == FieldTypeVO.SELECT:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(
                        name=field_name, sql_type="varchar(128)", nullable=nullable
                    ),
                )
            )

        if field.field_type == FieldTypeVO.ACTOR:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(name=field_name, sql_type="uuid", nullable=nullable),
                )
            )

        if field.field_type == FieldTypeVO.ADDRESS:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(
                        name=f"{field_name}_country",
                        sql_type="varchar(128)",
                        nullable=nullable,
                    ),
                    ColumnSpec(
                        name=f"{field_name}_region",
                        sql_type="varchar(128)",
                        nullable=nullable,
                    ),
                    ColumnSpec(
                        name=f"{field_name}_city",
                        sql_type="varchar(128)",
                        nullable=nullable,
                    ),
                    ColumnSpec(
                        name=f"{field_name}_address_line",
                        sql_type="varchar(255)",
                        nullable=nullable,
                    ),
                    ColumnSpec(
                        name=f"{field_name}_post_code",
                        sql_type="varchar(64)",
                        nullable=nullable,
                    ),
                )
            )

        if field.field_type == FieldTypeVO.FULL_NAME:
            full_name_settings = (
                field.settings
                if isinstance(field.settings, FullNameFieldSettings)
                else FullNameFieldSettings()
            )
            return _CompiledColumns(
                columns=(
                    ColumnSpec(
                        name=f"{field_name}_last_name",
                        sql_type="varchar(128)",
                        nullable=nullable or not full_name_settings.require_last_name,
                    ),
                    ColumnSpec(
                        name=f"{field_name}_middle_name",
                        sql_type="varchar(128)",
                        nullable=nullable or not full_name_settings.require_middle_name,
                    ),
                    ColumnSpec(
                        name=f"{field_name}_first_name",
                        sql_type="varchar(128)",
                        nullable=nullable or not full_name_settings.require_first_name,
                    ),
                )
            )

        if field.field_type == FieldTypeVO.CURRENCY:
            return _CompiledColumns(
                columns=(
                    ColumnSpec(
                        name=f"{field_name}_amount_minor",
                        sql_type="bigint",
                        nullable=nullable,
                    ),
                    ColumnSpec(
                        name=f"{field_name}_currency",
                        sql_type="varchar(3)",
                        nullable=nullable,
                    ),
                )
            )

        if field.field_type == FieldTypeVO.RELATION:
            relation_settings = (
                field.settings
                if isinstance(field.settings, RelationFieldSettings)
                else RelationFieldSettings()
            )
            if relation_settings.max_links != 1:
                return _CompiledColumns(columns=tuple(), is_virtual=True)
            target_table = None
            target_column = None
            if (
                field.relation_target_object_id is not None
                and object_table_name_by_id is not None
            ):
                target_table = object_table_name_by_id.get(
                    str(field.relation_target_object_id.value)
                )
                if target_table is not None:
                    target_column = "id"
            return _CompiledColumns(
                columns=(
                    ColumnSpec(
                        name=field_name,
                        sql_type="uuid",
                        nullable=nullable,
                        references_table=target_table,
                        references_column=target_column,
                        on_delete=relation_settings.on_delete,
                    ),
                )
            )

        return _CompiledColumns(columns=tuple(), is_virtual=True)

    @staticmethod
    def _index_name(
        *, prefix: str, table_name: str, column_names: tuple[str, ...]
    ) -> str:
        suffix = "_".join(column_names)
        normalized = f"{prefix}_{table_name}_{suffix}".lower()
        return normalized[:63]

    def _append_entity_owner_index(
        self,
        *,
        table_name: str,
        columns: list[ColumnSpec],
        indexes: list[IndexSpec],
    ) -> None:
        """
        Owner composite key for polymorphic children:
        (entity_name, entity_uuid).
        """
        owner_columns = ("entity_name", "entity_uuid")
        if not all(
            any(column.name == owner_column for column in columns)
            for owner_column in owner_columns
        ):
            return
        if any(index.columns == owner_columns for index in indexes):
            return
        indexes.append(
            IndexSpec(
                name=self._index_name(
                    prefix="ix",
                    table_name=table_name,
                    column_names=owner_columns,
                ),
                columns=owner_columns,
                unique=False,
            )
        )


__all__ = ["FieldLayoutCompiler"]

from __future__ import annotations

from dataclasses import dataclass

from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import FieldName, FieldTypeVO
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.object.value_object import ObjectLabelVO, ObjectNameVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.contracts import (
    MetadataCompilerProtocol,
)
from src.modules.runtime_schema.infrastructure.ddl_models import (
    LoadedSystemManifest,
    MetadataBundle,
    SystemFieldDefinition,
)
from src.modules.runtime_schema.infrastructure.field_serialization import (
    deserialize_field_default,
    deserialize_field_options,
    deserialize_field_settings,
)
from src.modules.shared.domain.errors import ValidationError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class _PendingRelationFieldTarget:
    source_object_key: str
    source_field_name: str
    target_object_key: str
    target_field_name: str


class MetadataCompiler(MetadataCompilerProtocol):
    def compile_system_schema(
        self,
        *,
        manifest: LoadedSystemManifest,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
    ) -> MetadataBundle:
        objects_by_key: dict[str, ObjectMetadataEntity] = {}
        fields_by_object_key: dict[str, tuple[FieldMetadataEntity, ...]] = {}
        pending_field_targets: list[_PendingRelationFieldTarget] = []

        for object_definition in manifest.objects:
            object_entity = ObjectMetadataEntity.create(
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                object_name=ObjectNameVO(
                    name_singular=object_definition.name_singular,
                    name_plural=object_definition.name_plural,
                ),
                object_label=ObjectLabelVO(
                    name_singular=object_definition.label_singular,
                    name_plural=object_definition.label_plural,
                ),
                description=object_definition.description,
                icon=object_definition.icon,
                shortcut=object_definition.shortcut,
                duplicate_criteria=object_definition.duplicate_criteria,
            )
            objects_by_key[object_definition.key] = object_entity

        for object_definition in manifest.objects:
            object_entity = objects_by_key[object_definition.key]
            object_fields: list[FieldMetadataEntity] = []
            for field_definition in object_definition.fields:
                object_fields.append(
                    self._compile_field(
                        field_definition=field_definition,
                        tenant_id=tenant_id,
                        object_metadata_id=object_entity.id,
                        object_id_by_key={
                            object_key: obj.id for object_key, obj in objects_by_key.items()
                        },
                        object_key=object_definition.key,
                        pending_field_targets=pending_field_targets,
                    )
                )
            fields_by_object_key[object_definition.key] = tuple(object_fields)

        field_id_by_object_and_name: dict[tuple[str, str], object] = {}
        for object_key, object_fields in fields_by_object_key.items():
            for field_entity in object_fields:
                field_id_by_object_and_name[(object_key, field_entity.field_name.value)] = (
                    field_entity.id
                )

        for pending in pending_field_targets:
            source_fields = fields_by_object_key[pending.source_object_key]
            source_field = next(
                (
                    item
                    for item in source_fields
                    if item.field_name.value == pending.source_field_name
                ),
                None,
            )
            if source_field is None:
                raise ValidationError(
                    f"relation source field '{pending.source_object_key}.{pending.source_field_name}' was not found"
                )
            target_field_id = field_id_by_object_and_name.get(
                (pending.target_object_key, pending.target_field_name)
            )
            if target_field_id is None:
                raise ValidationError(
                    f"relation target field '{pending.target_object_key}.{pending.target_field_name}' was not found"
                )
            source_field.set_relation_target(
                target_object_id=objects_by_key[pending.target_object_key].id,
                target_field_id=target_field_id,
            )

        return MetadataBundle(
            version=manifest.version,
            manifest_hash=manifest.manifest_hash,
            objects_by_key=objects_by_key,
            fields_by_object_key=fields_by_object_key,
        )

    @staticmethod
    def _compile_field(
        *,
        field_definition: SystemFieldDefinition,
        tenant_id: EntityIdVO,
        object_metadata_id: object,
        object_id_by_key: dict[str, object],
        object_key: str,
        pending_field_targets: list[_PendingRelationFieldTarget],
    ) -> FieldMetadataEntity:
        try:
            field_type = FieldTypeVO(field_definition.field_type.strip().lower())
        except ValueError as exc:
            raise ValidationError(
                f"field '{object_key}.{field_definition.name}' has unsupported type '{field_definition.field_type}'"
            ) from exc

        if field_definition.relation_target_object is not None:
            relation_target_object_id = object_id_by_key.get(
                field_definition.relation_target_object
            )
            if relation_target_object_id is None:
                raise ValidationError(
                    f"field '{object_key}.{field_definition.name}' relation_target_object "
                    f"'{field_definition.relation_target_object}' does not exist"
                )
        else:
            relation_target_object_id = None

        try:
            options = deserialize_field_options(
                field_type=field_type,
                payload=field_definition.options,
            )
            settings = deserialize_field_settings(
                field_type=field_type,
                payload=field_definition.settings,
            )
            default_value = deserialize_field_default(
                field_type=field_type,
                payload=field_definition.default_value,
            )
        except Exception as exc:
            raise ValidationError(
                f"field '{object_key}.{field_definition.name}' options/settings/default are invalid: {exc}"
            ) from exc

        entity = FieldMetadataEntity.create(
            tenant_id=tenant_id,
            object_metadata_id=object_metadata_id,
            field_type=field_type,
            field_name=FieldName(field_definition.name),
            label=field_definition.label,
            description=field_definition.description,
            icon=field_definition.icon,
            is_unique=field_definition.is_unique,
            is_index=field_definition.is_index,
            is_nullable=field_definition.is_nullable,
            is_ui_read_only=field_definition.is_ui_read_only,
            is_searchable=field_definition.is_searchable,
            options=options,
            settings=settings,
            default_value=default_value,
            relation_target_object_id=relation_target_object_id,
            relation_target_field_id=None,
        )

        if field_definition.relation_target_field:
            if field_definition.relation_target_object is None:
                raise ValidationError(
                    f"field '{object_key}.{field_definition.name}' relation_target_field requires relation_target_object"
                )
            pending_field_targets.append(
                _PendingRelationFieldTarget(
                    source_object_key=object_key,
                    source_field_name=field_definition.name.strip().lower(),
                    target_object_key=field_definition.relation_target_object,
                    target_field_name=field_definition.relation_target_field.strip().lower(),
                )
            )
        return entity


__all__ = ["MetadataCompiler"]

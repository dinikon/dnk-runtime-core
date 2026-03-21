from datetime import datetime
from typing import Sequence

from src.modules.schema_registry.domain.error import (
    ObjectNameAlreadyExistsError,
    ObjectNotFoundError,
)
from src.modules.schema_registry.domain.field.entity import FieldEntity
from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO
from src.modules.schema_registry.domain.field_seed import FieldSeed
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.repository import (
    ObjectRepositoryProtocol,
)
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.shared import EntityIdVO


class SchemaRegistryDomainService:
    def __init__(self, object_repository: ObjectRepositoryProtocol) -> None:
        self._object_repository = object_repository

    def create_object(
        self,
        *,
        object_id: EntityIdVO,
        tenant_id: EntityIdVO,
        now: datetime,
        singular_name: str,
        plural_name: str,
        label_singular: str,
        label_plural: str,
        description: str,
        fields: Sequence[FieldSeed] = (),
    ) -> ObjectEntity:
        existing = self._object_repository.get_by_tenant_and_plural_name(
            tenant_id=tenant_id,
            plural_name=plural_name,
        )
        if existing is not None:
            raise ObjectNameAlreadyExistsError(
                f"Object with plural_name '{plural_name}' already exists."
            )

        object_entity = ObjectEntity.create(
            id_=object_id,
            tenant_id=tenant_id,
            now=now,
            object_name=ObjectNameVO(
                singular=singular_name,
                plural=plural_name,
            ),
            object_label=ObjectLabelVO(
                singular=label_singular,
                plural=label_plural,
            ),
            description=description,
        )

        if fields:
            object_entity.add_fields_from_seed(
                now=now,
                seeds=fields,
            )

        self._object_repository.save(object_entity)
        return object_entity

    def rename_object(
        self,
        *,
        object_id: EntityIdVO,
        now: datetime,
        singular_name: str,
        plural_name: str,
        label_singular: str,
        label_plural: str,
        description: str,
    ) -> ObjectEntity:
        object_entity = self._get_required_object(object_id)

        existing = self._object_repository.get_by_tenant_and_plural_name(
            tenant_id=object_entity.tenant_id,
            plural_name=plural_name,
        )
        if existing is not None and existing.id != object_entity.id:
            raise ObjectNameAlreadyExistsError(
                f"Object with plural_name '{plural_name}' already exists."
            )

        object_entity.rename(
            now=now,
            object_name=ObjectNameVO(
                singular=singular_name,
                plural=plural_name,
            ),
            object_label=ObjectLabelVO(
                singular=label_singular,
                plural=label_plural,
            ),
            description=description,
        )
        self._object_repository.save(object_entity)
        return object_entity

    def delete_object(
        self,
        *,
        object_id: EntityIdVO,
    ) -> None:
        object_entity = self._get_required_object(object_id)
        self._object_repository.delete(object_entity.id)

    def add_field(
        self,
        *,
        object_id: EntityIdVO,
        field_id: EntityIdVO,
        now: datetime,
        field_name: str,
        field_type: FieldTypeVO,
        label: str,
        description: str,
        is_nullable: bool,
        options: dict[str, str] | None = None,
        settings: dict[str, str] | None = None,
    ) -> FieldEntity:
        object_entity = self._get_required_object(object_id)

        field_entity = object_entity.add_field(
            field_id=field_id,
            now=now,
            field_name=field_name,
            field_type=field_type,
            label=label,
            description=description,
            is_nullable=is_nullable,
            options=options,
            settings=settings,
        )
        self._object_repository.save(object_entity)
        return field_entity

    def rename_field(
        self,
        *,
        object_id: EntityIdVO,
        field_id: EntityIdVO,
        now: datetime,
        field_name: str,
        label: str,
        description: str,
    ) -> ObjectEntity:
        object_entity = self._get_required_object(object_id)
        object_entity.rename_field(
            field_id=field_id,
            now=now,
            field_name=field_name,
            label=label,
            description=description,
        )
        self._object_repository.save(object_entity)
        return object_entity

    def delete_field(
        self,
        *,
        object_id: EntityIdVO,
        field_id: EntityIdVO,
        now: datetime,
    ) -> ObjectEntity:
        object_entity = self._get_required_object(object_id)
        object_entity.remove_field(
            field_id=field_id,
            now=now,
        )
        self._object_repository.save(object_entity)
        return object_entity

    def replace_field_settings(
        self,
        *,
        object_id: EntityIdVO,
        field_id: EntityIdVO,
        now: datetime,
        settings: dict[str, str],
    ) -> ObjectEntity:
        object_entity = self._get_required_object(object_id)
        object_entity.replace_field_settings(
            field_id=field_id,
            now=now,
            settings=settings,
        )
        self._object_repository.save(object_entity)
        return object_entity

    def merge_field_settings(
        self,
        *,
        object_id: EntityIdVO,
        field_id: EntityIdVO,
        now: datetime,
        patch: dict[str, str],
    ) -> ObjectEntity:
        object_entity = self._get_required_object(object_id)
        object_entity.merge_field_settings(
            field_id=field_id,
            now=now,
            patch=patch,
        )
        self._object_repository.save(object_entity)
        return object_entity

    def replace_field_options(
        self,
        *,
        object_id: EntityIdVO,
        field_id: EntityIdVO,
        now: datetime,
        options: dict[str, str],
    ) -> ObjectEntity:
        object_entity = self._get_required_object(object_id)
        object_entity.replace_field_options(
            field_id=field_id,
            now=now,
            options=options,
        )
        self._object_repository.save(object_entity)
        return object_entity

    def _get_required_object(self, object_id: EntityIdVO) -> ObjectEntity:
        object_entity = self._object_repository.load(object_id)
        if object_entity is None:
            raise ObjectNotFoundError(f"Object {object_id} not found.")
        return object_entity

from dataclasses import dataclass, field
from datetime import datetime
from collections.abc import Callable, Sequence
from typing import Self

from src.modules.schema_registry.domain.error import (
    FieldNotFoundError,
    FieldAlreadyExistsError,
)
from src.modules.schema_registry.domain.field.entity import FieldEntity
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.field.value_object.field_label import (
    FieldLabelVO,
)
from src.modules.schema_registry.domain.field.value_object.field_name import FieldNameVO
from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class ObjectEntity:
    """Доменная сущность runtime-объекта и его полей в metadata."""

    id: EntityIdVO
    created_at: datetime
    updated_at: datetime

    tenant_id: EntityIdVO
    data_source_id: EntityIdVO

    kind: ObjectKind
    object_name: ObjectNameVO
    object_label: ObjectLabelVO

    description: str

    fields: list[FieldEntity] = field(default_factory=list)

    @property
    def model_name(self) -> str:
        """Возвращает singular-имя как имя доменной модели."""
        return self.object_name.singular

    @classmethod
    def create(
        cls,
        *,
        id_: EntityIdVO,
        tenant_id: EntityIdVO,
        data_source_id: EntityIdVO,
        now: datetime,
        object_name: ObjectNameVO,
        object_label: ObjectLabelVO,
        description: str,
        kind: ObjectKind = ObjectKind.STANDARD,
    ) -> Self:
        """Создает runtime-объект без полей и нормализует description."""
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            kind=kind,
            object_name=object_name,
            object_label=object_label,
            description=description.strip(),
            fields=[],
        )

    def rename(
        self,
        *,
        now: datetime,
        object_name: ObjectNameVO,
        object_label: ObjectLabelVO,
        description: str,
        kind: ObjectKind | None = None,
    ) -> None:
        """Обновляет имя, label и description runtime-объекта."""
        if kind is not None:
            self.kind = kind
        self.object_name = object_name
        self.object_label = object_label
        self.description = description.strip()
        self.updated_at = now

    def add_field(
        self,
        *,
        field_id: EntityIdVO,
        now: datetime,
        field_name: str,
        field_type: FieldTypeVO,
        label: str,
        description: str,
        is_nullable: bool,
        default_value: str | None = None,
        options: dict[str, str] | None = None,
        settings: dict[str, str] | None = None,
        kind: FieldKind = FieldKind.STANDARD,
    ) -> FieldEntity:
        """Добавляет новое поле в объект, проверяя уникальность имени."""
        self._ensure_field_name_is_unique(field_name=field_name)

        field_entity = FieldEntity.create(
            id_=field_id,
            object_id=self.id,
            now=now,
            field_name=FieldNameVO(field_name),
            field_type=field_type,
            kind=kind,
            label=FieldLabelVO(label),
            description=description,
            is_nullable=is_nullable,
            default_value=default_value,
            options=options,
            settings=settings,
        )
        self.fields.append(field_entity)
        self.updated_at = now
        return field_entity

    def add_fields_from_seed(
        self,
        *,
        now: datetime,
        seeds: Sequence[FieldSeed],
        field_id_provider: Callable[[], EntityIdVO],
        field_type_mapper: Callable[[str], FieldTypeVO],
    ) -> None:
        """Массово добавляет поля из raw seed через переданный mapper типов."""
        for seed in seeds:
            self.add_field(
                field_id=field_id_provider(),
                now=now,
                field_name=seed.name,
                field_type=field_type_mapper(seed.type),
                label=seed.label,
                description=seed.description,
                is_nullable=seed.is_nullable,
                default_value=seed.default,
                options=seed.options,
                settings=seed.settings,
                kind=FieldKind.from_value(seed.kind),
            )

    def rename_field(
        self,
        *,
        field_id: EntityIdVO,
        now: datetime,
        field_name: str,
        label: str,
        description: str,
    ) -> None:
        """Переименовывает поле и обновляет его человекочитаемые metadata."""
        field_entity = self.get_field(field_id)

        self._ensure_field_name_is_unique(
            field_name=field_name,
            exclude_field_id=field_id,
        )

        field_entity.rename(
            now=now,
            field_name=FieldNameVO(field_name),
            label=FieldLabelVO(label),
            description=description,
        )
        self.updated_at = now

    def remove_field(
        self,
        *,
        field_id: EntityIdVO,
        now: datetime,
    ) -> FieldEntity:
        """Удаляет поле из объекта и возвращает удаленную сущность."""
        field_entity = self.get_field(field_id)
        self.fields = [_field for _field in self.fields if _field.id != field_id]
        self.updated_at = now
        return field_entity

    def replace_field_settings(
        self,
        *,
        field_id: EntityIdVO,
        now: datetime,
        settings: dict[str, str],
    ) -> None:
        """Полностью заменяет settings выбранного поля."""
        field_entity = self.get_field(field_id)
        field_entity.replace_settings(now=now, settings=settings)
        self.updated_at = now

    def merge_field_settings(
        self,
        *,
        field_id: EntityIdVO,
        now: datetime,
        patch: dict[str, str],
    ) -> None:
        """Сливает patch в settings выбранного поля."""
        field_entity = self.get_field(field_id)
        field_entity.merge_settings(now=now, patch=patch)
        self.updated_at = now

    def replace_field_options(
        self,
        *,
        field_id: EntityIdVO,
        now: datetime,
        options: dict[str, str],
    ) -> None:
        """Полностью заменяет options выбранного поля."""
        field_entity = self.get_field(field_id)
        field_entity.replace_options(now=now, options=options)
        self.updated_at = now

    def get_field(self, field_id: EntityIdVO) -> FieldEntity:
        """Возвращает поле по id или поднимает FieldNotFoundError."""
        for field_entity in self.fields:
            if field_entity.id == field_id:
                return field_entity
        raise FieldNotFoundError(f"Field {field_id} not found.")

    def get_field_by_name(self, field_name: str) -> FieldEntity | None:
        """Ищет поле по имени после trim входного значения."""
        normalized = field_name.strip()
        for field_entity in self.fields:
            if field_entity.field_name.value == normalized:
                return field_entity
        return None

    def _ensure_field_name_is_unique(
        self,
        *,
        field_name: str,
        exclude_field_id: EntityIdVO | None = None,
    ) -> None:
        """Проверяет уникальность имени поля внутри объекта."""
        normalized = field_name.strip()

        for field_entity in self.fields:
            if exclude_field_id is not None and field_entity.id == exclude_field_id:
                continue

            if field_entity.field_name.value == normalized:
                raise FieldAlreadyExistsError(
                    f"Field with name '{normalized}' already exists in object '{self.id}'."
                )

    def is_visible_in_catalog(self) -> bool:
        """Проверяет, нужно ли показывать объект в UI-каталоге объектов."""
        return self.kind != ObjectKind.SYSTEM

    def can_add_custom_fields(self) -> bool:
        """Проверяет, можно ли расширять объект пользовательскими полями."""
        return self.kind in {ObjectKind.CUSTOM, ObjectKind.STANDARD}

    def can_delete(self) -> bool:
        """Проверяет, можно ли удалить объект как пользовательский."""
        return self.kind == ObjectKind.CUSTOM

    def is_read_only(self) -> bool:
        """Проверяет metadata-only read-only режим для будущих view-объектов."""
        return self.kind == ObjectKind.VIEW

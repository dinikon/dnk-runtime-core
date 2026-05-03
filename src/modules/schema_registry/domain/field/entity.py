from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.schema_registry.domain.error import InvalidFieldOperationError
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.field.value_object.field_label import (
    FieldLabelVO,
)
from src.modules.schema_registry.domain.field.value_object.field_name import FieldNameVO
from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO
from src.modules.schema_registry.domain.field.value_object.runtime_field_id import (
    RuntimeFieldIdVO,
)
from src.modules.schema_registry.domain.object.value_object.runtime_object_id import (
    RuntimeObjectIdVO,
)


@dataclass(slots=True)
class FieldEntity:
    """Доменная сущность поля runtime-объекта в metadata schema_registry."""

    id: RuntimeFieldIdVO
    created_at: datetime
    updated_at: datetime

    object_id: RuntimeObjectIdVO

    kind: FieldKind
    field_name: FieldNameVO
    field_type: FieldTypeVO

    label: FieldLabelVO
    description: str

    is_nullable: bool
    default_value: str | None

    options: dict[str, str]
    settings: dict[str, str]

    @classmethod
    def create(
        cls,
        *,
        id_: RuntimeFieldIdVO,
        now: datetime,
        object_id: RuntimeObjectIdVO,
        field_name: FieldNameVO,
        field_type: FieldTypeVO,
        label: FieldLabelVO,
        description: str,
        is_nullable: bool,
        default_value: str | None = None,
        options: dict[str, str] | None = None,
        settings: dict[str, str] | None = None,
        kind: FieldKind = FieldKind.STANDARD,
    ) -> Self:
        """Создает поле и нормализует description/default/options/settings."""
        normalized_description = description.strip()
        normalized_options = dict(options or {})
        normalized_settings = dict(settings or {})
        normalized_default_value = default_value.strip() if default_value else None

        if normalized_options and not field_type.is_select_like():
            raise InvalidFieldOperationError(
                "Options are allowed only for select/multiselect fields."
            )

        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            object_id=object_id,
            kind=kind,
            field_name=field_name,
            field_type=field_type,
            label=label,
            description=normalized_description,
            is_nullable=is_nullable,
            default_value=normalized_default_value,
            options=normalized_options,
            settings=normalized_settings,
        )

    def rename(
        self,
        *,
        now: datetime,
        field_name: FieldNameVO,
        label: FieldLabelVO,
        description: str,
    ) -> None:
        """Обновляет имя и человекочитаемые metadata поля."""
        self.field_name = field_name
        self.label = label
        self.description = description.strip()
        self.updated_at = now

    def replace_settings(
        self,
        *,
        now: datetime,
        settings: dict[str, str],
    ) -> None:
        """Полностью заменяет settings поля."""
        self.settings = dict(settings)
        self.updated_at = now

    def merge_settings(
        self,
        *,
        now: datetime,
        patch: dict[str, str],
    ) -> None:
        """Сливает patch в текущие settings поля."""
        new_settings = dict(self.settings)
        new_settings.update(patch)
        self.settings = new_settings
        self.updated_at = now

    def replace_options(
        self,
        *,
        now: datetime,
        options: dict[str, str],
    ) -> None:
        """Полностью заменяет options, разрешая их только select-like типам."""
        if options and not self.field_type.is_select_like():
            raise InvalidFieldOperationError(
                "Options are allowed only for select/multiselect fields."
            )

        self.options = dict(options)
        self.updated_at = now

    def clear_options(self, *, now: datetime) -> None:
        """Очищает options поля и обновляет timestamp."""
        self.options = {}
        self.updated_at = now

    def update_from_spec(
        self,
        *,
        now: datetime,
        field_name: FieldNameVO,
        field_type: FieldTypeVO,
        kind: FieldKind,
        label: FieldLabelVO,
        description: str,
        is_nullable: bool,
        default_value: str | None,
        options: dict[str, str],
        settings: dict[str, str],
    ) -> bool:
        """Применяет валидированную spec к полю и возвращает факт изменения."""
        if options and not field_type.is_select_like():
            raise InvalidFieldOperationError(
                "Options are allowed only for select/multiselect fields."
            )

        normalized_description = description.strip()
        normalized_default_value = default_value.strip() if default_value else None
        normalized_options = dict(options)
        normalized_settings = dict(settings)

        if (
            self.field_name == field_name
            and self.field_type == field_type
            and self.kind == kind
            and self.label == label
            and self.description == normalized_description
            and self.is_nullable == is_nullable
            and self.default_value == normalized_default_value
            and self.options == normalized_options
            and self.settings == normalized_settings
        ):
            return False

        self.field_name = field_name
        self.field_type = field_type
        self.kind = kind
        self.label = label
        self.description = normalized_description
        self.is_nullable = is_nullable
        self.default_value = normalized_default_value
        self.options = normalized_options
        self.settings = normalized_settings
        self.updated_at = now
        return True

    def change_type(self, *args: object, **kwargs: object) -> None:
        """Явно запрещает изменение типа существующего поля в MVP."""
        raise InvalidFieldOperationError(
            "Changing field type is forbidden for existing field in MVP."
        )

    def can_delete(self) -> bool:
        """Проверяет, можно ли удалить поле как пользовательское."""
        return self.kind == FieldKind.CUSTOM

    def can_patch(self) -> bool:
        """Проверяет, можно ли менять runtime-значение поля напрямую."""
        return self.kind != FieldKind.SYSTEM

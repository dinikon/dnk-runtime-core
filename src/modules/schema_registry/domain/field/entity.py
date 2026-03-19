from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.schema_registry.domain.error import InvalidFieldOperationError
from src.modules.schema_registry.domain.field.value_object.field_label import (
    FieldLabelVO,
)
from src.modules.schema_registry.domain.field.value_object.field_name import FieldNameVO
from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class FieldEntity:
    id: EntityIdVO
    created_at: datetime
    updated_at: datetime

    object_id: EntityIdVO

    field_name: FieldNameVO
    field_type: FieldTypeVO

    label: FieldLabelVO
    description: str

    is_nullable: bool

    options: dict[str, str]
    settings: dict[str, str]

    @classmethod
    def create(
        cls,
        *,
        id_: EntityIdVO,
        now: datetime,
        object_id: EntityIdVO,
        field_name: FieldNameVO,
        field_type: FieldTypeVO,
        label: FieldLabelVO,
        description: str,
        is_nullable: bool,
        options: dict[str, str] | None = None,
        settings: dict[str, str] | None = None,
    ) -> Self:
        normalized_description = description.strip()
        normalized_options = dict(options or {})
        normalized_settings = dict(settings or {})

        if normalized_options and not field_type.is_select_like():
            raise InvalidFieldOperationError(
                "Options are allowed only for select/multiselect fields."
            )

        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            object_id=object_id,
            field_name=field_name,
            field_type=field_type,
            label=label,
            description=normalized_description,
            is_nullable=is_nullable,
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
        self.settings = dict(settings)
        self.updated_at = now

    def merge_settings(
        self,
        *,
        now: datetime,
        patch: dict[str, str],
    ) -> None:
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
        if options and not self.field_type.is_select_like():
            raise InvalidFieldOperationError(
                "Options are allowed only for select/multiselect fields."
            )

        self.options = dict(options)
        self.updated_at = now

    def clear_options(self, *, now: datetime) -> None:
        self.options = {}
        self.updated_at = now

    def change_type(self, *args, **kwargs) -> None:
        raise InvalidFieldOperationError(
            "Changing field type is forbidden for existing field in MVP."
        )

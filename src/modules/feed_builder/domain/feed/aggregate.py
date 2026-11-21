from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_code import FeedCodeVO
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.error import (
    DuplicateFieldIdentifierError,
    DuplicateFieldKeyError,
    DuplicateExportNameError,
    InvalidFeedValueError,
)


@dataclass(frozen=True, slots=True)
class Feed:
    """Корневой агрегат пользовательской схемы и настроек выгрузки."""

    id: FeedIdVO
    created_at: datetime
    updated_at: datetime
    name: FeedNameVO
    code: FeedCodeVO
    status: FeedStatus
    schema: FeedSchemaVO
    export_settings: FeedExportSettingsVO

    @classmethod
    def create(
        cls,
        *,
        identifier: FeedIdVO,
        name: FeedNameVO,
        code: FeedCodeVO,
        now: datetime,
        export_settings: FeedExportSettingsVO,
        schema: FeedSchemaVO | None = None,
    ) -> Self:
        """Создаёт DRAFT с явными настройками экспорта и пустой либо переданной схемой."""
        return cls.restore(
            identifier=identifier,
            name=name,
            code=code,
            status=FeedStatus.DRAFT,
            schema=FeedSchemaVO() if schema is None else schema,
            export_settings=export_settings,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: FeedIdVO,
        name: FeedNameVO,
        code: FeedCodeVO,
        status: FeedStatus,
        schema: FeedSchemaVO,
        export_settings: FeedExportSettingsVO,
        created_at: datetime,
        updated_at: datetime,
    ) -> Self:
        """Восстанавливает состав и проверяет собственные инварианты без I/O."""
        if (
            not isinstance(identifier, FeedIdVO)
            or not isinstance(name, FeedNameVO)
            or not isinstance(code, FeedCodeVO)
            or not isinstance(status, FeedStatus)
            or not isinstance(schema, FeedSchemaVO)
            or not isinstance(export_settings, FeedExportSettingsVO)
        ):
            raise InvalidFeedValueError("Нужны типизированные свойства Feed.")
        for value in (created_at, updated_at):
            if (
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise InvalidFeedValueError("Даты Feed должны иметь timezone.")
        if updated_at < created_at:
            raise InvalidFeedValueError(
                "Изменение Feed не может предшествовать созданию."
            )
        identifiers, keys, export_names = set(), set(), set()
        restored_fields: list[FieldDefinition] = []
        for index, definition in enumerate(schema.fields):
            definition = FieldDefinition.restore(
                identifier=definition.id,
                key=definition.key,
                label=definition.label,
                type_definition=definition.type_definition,
                export=definition.export,
                ai_instruction=definition.ai_instruction,
            )
            if definition.id in identifiers:
                raise DuplicateFieldIdentifierError(
                    "Field ID повторяется в Feed.",
                    path=("schema", "fields", index, "id"),
                )
            if definition.key in keys:
                raise DuplicateFieldKeyError(
                    "Ключ поля повторяется в Feed.",
                    path=("schema", "fields", index, "key"),
                )
            if definition.export.name in export_names:
                raise DuplicateExportNameError(
                    "Экспортное имя повторяется в Feed.",
                    path=("schema", "fields", index, "export", "name"),
                )
            identifiers.add(definition.id)
            keys.add(definition.key)
            export_names.add(definition.export.name)
            restored_fields.append(definition)
        schema = FeedSchemaVO(tuple(restored_fields), schema.schema_format_version)
        return cls(
            id=identifier,
            name=name,
            code=code,
            status=status,
            schema=schema,
            export_settings=export_settings,
            created_at=created_at,
            updated_at=updated_at,
        )

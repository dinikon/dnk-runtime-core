from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
    LocalizedOverridesVO,
    ItemOverridesVO,
)
from src.modules.channels.domain.product_representation.value_object import ContentImage
from src.modules.channels.domain.types import JsonObject
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

OVERRIDES_SCHEMA = "representation_overrides.v1"


class StoredImage(BaseModel):
    """Конкретное представление ссылки на изображение в JSONB."""

    model_config = ConfigDict(extra="forbid")
    file_id: UUID
    alt: str = ""
    caption: str = ""


class StoredLocalizedOverrides(BaseModel):
    """Конкретные поля одного языка без произвольного документа настроек."""

    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    body: str | None = None
    gallery: tuple[StoredImage, ...] | None = None

    def to_value(self, locale: str) -> LocalizedOverridesVO:
        """Восстанавливает неизменяемое значение с доменной проверкой."""
        return LocalizedOverridesVO(
            locale,
            self.title,
            self.body,
            (
                tuple(
                    ContentImage(EntityIdVO(image.file_id), image.alt, image.caption)
                    for image in self.gallery
                )
                if self.gallery is not None
                else None
            ),
        )


class StoredOverrides(BaseModel):
    """Версионированный документ хранения конкретной модели overrides."""

    model_config = ConfigDict(extra="forbid")
    common: dict[str, StoredLocalizedOverrides]
    items: dict[UUID, dict[str, StoredLocalizedOverrides]]


def decode_overrides(*, schema: str, document: JsonObject) -> RepresentationOverridesVO:
    """Декодирует только поддержанный формат, не исправляя повреждённую запись."""
    if schema != OVERRIDES_SCHEMA:
        raise ChannelInputError("representation_schema_unsupported")
    try:
        value = StoredOverrides.model_validate(document)
    except ValidationError:
        raise ChannelInputError("representation_stored_invalid") from None
    return RepresentationOverridesVO(
        tuple(fields.to_value(locale) for locale, fields in value.common.items()),
        tuple(
            ItemOverridesVO(
                EntityIdVO(identifier),
                tuple(fields.to_value(locale) for locale, fields in content.items()),
            )
            for identifier, content in value.items.items()
        ),
    )


def encode_localized(value: LocalizedOverridesVO) -> JsonObject:
    """Пропускает наследуемые поля, сохраняя явную очистку."""
    result: JsonObject = {}
    if value.title is not None:
        result["title"] = value.title
    if value.body is not None:
        result["body"] = value.body
    if value.gallery is not None:
        result["gallery"] = [
            {
                "file_id": str(image.file_id.uuid),
                "alt": image.alt,
                "caption": image.caption,
            }
            for image in value.gallery
        ]
    return result


def encode_overrides(value: RepresentationOverridesVO) -> JsonObject:
    """Явно сериализует каноническое намерение в JSONB."""
    return {
        "common": {fields.locale: encode_localized(fields) for fields in value.common},
        "items": {
            str(item.binding_item_id.uuid): {
                fields.locale: encode_localized(fields) for fields in item.content
            }
            for item in value.items
        },
    }

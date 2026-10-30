from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
    LocalizedOverridesVO,
    ItemOverridesVO,
)
from src.modules.channels.domain.product_representation.value_object import ContentImage
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class RepresentationImageRequest(BaseModel):
    """Ссылка на готовое изображение без URL и координат storage."""

    model_config = ConfigDict(extra="forbid")
    file_id: UUID
    alt: str = ""
    caption: str = ""


class LocalizedOverridesRequest(BaseModel):
    """Явные поля одного языка; null и отсутствие возвращают наследование."""

    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    body: str | None = None
    gallery: tuple[RepresentationImageRequest, ...] | None = None

    def to_value(self, locale: str) -> LocalizedOverridesVO:
        """Передаёт в Domain конкретные неизменяемые значения."""
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


class RepresentationOverridesRequest(BaseModel):
    """Полный документ общих и индивидуальных overrides."""

    model_config = ConfigDict(extra="forbid")
    common: dict[str, LocalizedOverridesRequest] = Field(default_factory=dict)
    items: dict[UUID, dict[str, LocalizedOverridesRequest]] = Field(
        default_factory=dict
    )

    def to_value(self) -> RepresentationOverridesVO:
        """Не допускает неизвестные поля, модели платформ и произвольный Any."""
        return RepresentationOverridesVO(
            tuple(value.to_value(locale) for locale, value in self.common.items()),
            tuple(
                ItemOverridesVO(
                    EntityIdVO(identifier),
                    tuple(value.to_value(locale) for locale, value in content.items()),
                )
                for identifier, content in self.items.items()
            ),
        )

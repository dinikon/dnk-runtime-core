from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.channels.application.product_representation.contracts import (
    RepresentationState,
)
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
    LocalizedOverridesVO,
)


class RepresentationImageResponse(BaseModel):
    """Публичные поля изображения в overrides."""

    file_id: UUID
    alt: str
    caption: str


class LocalizedOverridesResponse(BaseModel):
    """Сохраняет различие наследования и явной очистки в HTTP."""

    title: str | None
    body: str | None
    gallery: tuple[RepresentationImageResponse, ...] | None

    @classmethod
    def from_value(cls, value: LocalizedOverridesVO) -> "LocalizedOverridesResponse":
        """Явно перечисляет публичные поля одного языка."""
        return cls(
            title=value.title,
            body=value.body,
            gallery=(
                tuple(
                    RepresentationImageResponse(
                        file_id=image.file_id.uuid, alt=image.alt, caption=image.caption
                    )
                    for image in value.gallery
                )
                if value.gallery is not None
                else None
            ),
        )


class RepresentationOverridesResponse(BaseModel):
    """Передаёт все локали и пары для полного сохранения редактором."""

    common: dict[str, LocalizedOverridesResponse]
    items: dict[str, dict[str, LocalizedOverridesResponse]]

    @classmethod
    def from_value(
        cls, value: RepresentationOverridesVO
    ) -> "RepresentationOverridesResponse":
        """Преобразует устойчивые ID в ключи JSON без автоматической сериализации Domain."""
        return cls(
            common={
                fields.locale: LocalizedOverridesResponse.from_value(fields)
                for fields in value.common
            },
            items={
                str(item.binding_item_id.uuid): {
                    fields.locale: LocalizedOverridesResponse.from_value(fields)
                    for fields in item.content
                }
                for item in value.items
            },
        )


class RepresentationStateResponse(BaseModel):
    """Общие публичные поля сохранённого состояния представления."""

    id: UUID | None
    revision: int
    export_enabled: bool
    overrides: RepresentationOverridesResponse
    created_at: datetime | None
    updated_at: datetime | None
    created_by: UUID | None
    updated_by: UUID | None

    @classmethod
    def from_state(cls, value: RepresentationState) -> "RepresentationStateResponse":
        """Не раскрывает формат хранения и технические документы."""
        return cls(
            id=value.id,
            revision=value.revision,
            export_enabled=value.export_enabled,
            overrides=RepresentationOverridesResponse.from_value(value.overrides),
            created_at=value.created_at,
            updated_at=value.updated_at,
            created_by=value.created_by,
            updated_by=value.updated_by,
        )


class RepresentationBindingItemResponse(BaseModel):
    """Связывает выбор позиции редактора со стабильным ID пары."""

    id: UUID
    catalog_position_id: UUID
    publication_id: UUID

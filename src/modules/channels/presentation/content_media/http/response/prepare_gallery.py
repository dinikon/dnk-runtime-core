from uuid import UUID
from pydantic import BaseModel

from src.modules.channels.application.content_media.command.prepare_gallery.dto import (
    PrepareGalleryResultDTO,
)


class PreparedGalleryImageResponse(BaseModel):
    """Публичная ссылка и данные позиции без hash/ciphertext токена."""

    media_id: UUID
    revision: int
    file_id: UUID
    alt: str
    caption: str
    remote_media_id: str | None
    transfer_status: str
    url: str


class PreparedGalleryResponse(BaseModel):
    """Одна цель и точная локаль; порядок images определяет главное изображение."""

    publication_id: UUID
    external_id: str
    parent_external_id: str | None
    publication_kind: str
    locale: str
    images: tuple[PreparedGalleryImageResponse, ...]


class PrepareGalleryResponse(BaseModel):
    """Контракт явной подготовки, отличный от read-only preview."""

    galleries: tuple[PreparedGalleryResponse, ...]

    @classmethod
    def from_dto(cls, result: PrepareGalleryResultDTO) -> "PrepareGalleryResponse":
        """Перечисляет поля без автоматической сериализации Domain или storage."""
        return cls(
            galleries=tuple(
                PreparedGalleryResponse(
                    publication_id=gallery.publication_id,
                    external_id=gallery.external_id,
                    parent_external_id=gallery.parent_external_id,
                    publication_kind=gallery.publication_kind,
                    locale=gallery.locale,
                    images=tuple(
                        PreparedGalleryImageResponse(
                            media_id=image.media_id,
                            revision=image.revision,
                            file_id=image.file_id,
                            alt=image.alt,
                            caption=image.caption,
                            remote_media_id=image.remote_media_id,
                            transfer_status=image.transfer_status.value,
                            url=image.url,
                        )
                        for image in gallery.images
                    ),
                )
                for gallery in result.galleries
            )
        )

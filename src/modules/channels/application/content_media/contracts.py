from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.modules.channels.domain.content_media.value_object import MediaTransferStatus
from src.modules.files.application.port.query_repository import FileContentLocationDTO
from src.modules.files.application.port.storage import FileContentStream


@dataclass(frozen=True, slots=True)
class MediaFile:
    """Снимок Files; координаты доступны только внутреннему адаптеру, не HTTP DTO."""

    file_id: UUID
    source_fingerprint: str
    extension: str
    location: FileContentLocationDTO = field(repr=False)


@dataclass(frozen=True, slots=True)
class MediaFileChecksum:
    """Контрольная сумма полностью прочитанного и проверенного owned-файла."""

    file_id: UUID
    sha256: str


@dataclass(frozen=True, slots=True)
class PreparedGalleryImage:
    """Одна позиция без потери порядка и метаданных представления."""

    media_id: UUID
    revision: int
    file_id: UUID
    alt: str
    caption: str
    remote_media_id: str | None
    transfer_status: MediaTransferStatus
    url: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class PreparedGallery:
    """Галерея конкретной цели и локали; первое изображение является главным."""

    publication_id: UUID
    external_id: str
    parent_external_id: str | None
    publication_kind: str
    locale: str
    images: tuple[PreparedGalleryImage, ...]


@dataclass(frozen=True, slots=True)
class MediaReadRow:
    """Проекция для доступа без восстановления Aggregate Root."""

    id: UUID
    connection_id: UUID
    channel_id: UUID
    file_id: UUID
    source_fingerprint: str
    metadata_fingerprint: str
    revision: int
    access_token_hash: bytes = field(repr=False)
    access_revoked_at: datetime | None
    transfer_status: MediaTransferStatus


@dataclass(frozen=True, slots=True)
class OpenMediaContent:
    """Управляемый поток после завершения SQL-транзакции."""

    content_type: str
    size_bytes: int
    stream: FileContentStream

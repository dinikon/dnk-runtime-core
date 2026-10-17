"""Тестовый потребитель: собственный порт и DTO поверх файлового адаптера."""

from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID

from src.modules.files.application.stored_file.command.upload_file.command import (
    UploadFileCommand,
)
from src.modules.files.application.stored_file.command.upload_file.handler import (
    UploadFileHandler,
)


@dataclass(frozen=True, slots=True)
class AttachmentReferenceDTO:
    """Результат тестового бизнес-порта, не DTO модуля Files."""

    file_id: UUID


class AttachmentStorageProtocol(Protocol):
    """Минимальный порт тестового бизнес-модуля."""

    async def upload(self, source: BinaryIO, size_bytes: int) -> AttachmentReferenceDTO:
        """Загружает вложение для сохранения ссылки в том же UoW."""
        ...


class FilesAttachmentAdapter:
    """Преобразует собственный контракт потребителя в Application контракт Files."""

    def __init__(self, tenant_id: UUID, upload: UploadFileHandler) -> None:
        """Принимает handler, собранный с сессией бизнес-транзакции."""
        self._tenant_id, self._upload = tenant_id, upload

    async def upload(self, source: BinaryIO, size_bytes: int) -> AttachmentReferenceDTO:
        """Не открывает новую транзакцию и не выполняет commit."""
        file = await self._upload.execute(
            UploadFileCommand(
                self._tenant_id,
                source,
                size_bytes,
                "attachment.bin",
                "application/octet-stream",
            )
        )
        return AttachmentReferenceDTO(file.file_id)

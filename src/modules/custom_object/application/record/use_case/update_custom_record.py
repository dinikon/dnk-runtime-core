from __future__ import annotations

from src.modules.custom_object.application.record.command import (
    UpdateCustomRecordCommand,
)
from src.modules.custom_object.application.record.dto import CustomRecordDTO
from src.modules.custom_object.application.record.repository import (
    CustomRecordRepositoryProtocol,
)


class UpdateCustomRecordUseCase:
    """Use case обновления runtime-записи кастомного объекта."""

    def __init__(self, repository: CustomRecordRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom records."""
        self._repository = repository

    async def __call__(self, command: UpdateCustomRecordCommand) -> CustomRecordDTO:
        """Обновляет runtime-запись кастомного объекта."""
        return await self._repository.update(command)


__all__ = ["UpdateCustomRecordUseCase"]

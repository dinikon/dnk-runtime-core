from __future__ import annotations

from src.modules.custom_object.application.record.command import CustomRecordByIdCommand
from src.modules.custom_object.application.record.dto import CustomRecordDTO
from src.modules.custom_object.application.record.repository import (
    CustomRecordRepositoryProtocol,
)


class GetCustomRecordUseCase:
    """Use case чтения runtime-записи кастомного объекта."""

    def __init__(self, repository: CustomRecordRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom records."""
        self._repository = repository

    async def __call__(self, command: CustomRecordByIdCommand) -> CustomRecordDTO:
        """Возвращает runtime-запись кастомного объекта."""
        return await self._repository.get(command)


__all__ = ["GetCustomRecordUseCase"]

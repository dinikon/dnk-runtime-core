from __future__ import annotations

from src.modules.custom_object.application.record.command import CustomRecordByIdCommand
from src.modules.custom_object.application.record.repository import (
    CustomRecordRepositoryProtocol,
)


class DeleteCustomRecordUseCase:
    """Use case удаления runtime-записи кастомного объекта."""

    def __init__(self, repository: CustomRecordRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom records."""
        self._repository = repository

    async def __call__(self, command: CustomRecordByIdCommand) -> None:
        """Удаляет runtime-запись кастомного объекта."""
        await self._repository.delete(command)


__all__ = ["DeleteCustomRecordUseCase"]

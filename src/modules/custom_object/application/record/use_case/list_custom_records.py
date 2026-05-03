from __future__ import annotations

from src.modules.custom_object.application.record.dto import CustomRecordDTO
from src.modules.custom_object.application.record.query import ListCustomRecordsQuery
from src.modules.custom_object.application.record.repository import (
    CustomRecordRepositoryProtocol,
)


class ListCustomRecordsUseCase:
    """Use case списка runtime-записей кастомного объекта."""

    def __init__(self, repository: CustomRecordRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom records."""
        self._repository = repository

    async def __call__(self, query: ListCustomRecordsQuery) -> list[CustomRecordDTO]:
        """Возвращает runtime-записи кастомного объекта."""
        return await self._repository.list(query)


__all__ = ["ListCustomRecordsUseCase"]

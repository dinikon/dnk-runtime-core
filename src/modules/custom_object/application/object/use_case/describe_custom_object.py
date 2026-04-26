from __future__ import annotations

from src.modules.custom_object.application.object.dto import CustomObjectDTO
from src.modules.custom_object.application.object.query import CustomObjectByIdQuery
from src.modules.custom_object.application.object.repository import (
    CustomObjectSchemaRepositoryProtocol,
)


class DescribeCustomObjectUseCase:
    """Use case чтения схемы кастомного объекта."""

    def __init__(self, repository: CustomObjectSchemaRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom objects."""
        self._repository = repository

    async def __call__(self, query: CustomObjectByIdQuery) -> CustomObjectDTO:
        """Возвращает схему кастомного объекта."""
        return await self._repository.describe_object(query)


__all__ = ["DescribeCustomObjectUseCase"]

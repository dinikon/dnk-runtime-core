from __future__ import annotations

from src.modules.schema_registry.application.config.object.dto import CustomObjectDTO
from src.modules.schema_registry.application.config.object.query import (
    CustomObjectByIdQuery,
)
from src.modules.schema_registry.application.config.object.repository import (
    SchemaConfigRepositoryProtocol,
)


class DescribeCustomObjectUseCase:
    """Use case чтения схемы кастомного объекта."""

    def __init__(self, repository: SchemaConfigRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом custom objects."""
        self._repository = repository

    async def __call__(self, query: CustomObjectByIdQuery) -> CustomObjectDTO:
        """Возвращает схему кастомного объекта."""
        return await self._repository.describe_object(query)


__all__ = ["DescribeCustomObjectUseCase"]

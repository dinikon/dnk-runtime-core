from __future__ import annotations

from typing import Protocol

from src.modules.runtime_schema.domain.schema.entity import DataSourceEntity


class DataSourceRepositoryProtocol(Protocol):
    async def add(self, entity: DataSourceEntity) -> DataSourceEntity: ...


# Backward compatibility alias.
DataSourceRepository = DataSourceRepositoryProtocol

__all__ = ["DataSourceRepository", "DataSourceRepositoryProtocol"]

from __future__ import annotations

from typing import Protocol

from src.modules.runtime_schema.application.schema.dto import (
    CreateSchemaCommandDTO,
    CreateSchemaResultDTO,
)
from src.modules.runtime_schema.domain.schema.entity import DataSourceEntity


class DataSourceWriteRepositoryProtocol(Protocol):
    async def add(self, entity: DataSourceEntity) -> DataSourceEntity: ...


class DatabaseSchemaRepositoryProtocol(Protocol):
    async def create_schema(self, schema_name: str) -> None: ...


class CreateSchemaUseCaseProtocol(Protocol):
    async def execute(self, dto: CreateSchemaCommandDTO) -> CreateSchemaResultDTO: ...


__all__ = [
    "CreateSchemaUseCaseProtocol",
    "DataSourceWriteRepositoryProtocol",
    "DatabaseSchemaRepositoryProtocol",
]


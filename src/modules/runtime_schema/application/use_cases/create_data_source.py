from __future__ import annotations

from src.modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.runtime_schema.application.commands import CreateDataSourceCommand
from src.modules.runtime_schema.application.dto import DataSourceDTO
from src.modules.runtime_schema.application.mappers import data_source_to_dto
from src.modules.runtime_schema.domain.entities import DataSource
from src.modules.runtime_schema.domain.repositories import DataSourceRepositoryProtocol


class CreateDataSourceUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        data_source_repository: DataSourceRepositoryProtocol,
    ):
        self._uow = uow
        self._data_source_repository = data_source_repository

    async def execute(self, command: CreateDataSourceCommand) -> DataSourceDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._create_within_transaction(command)
        return await self._create_within_transaction(command)

    async def _create_within_transaction(
        self,
        command: CreateDataSourceCommand,
    ) -> DataSourceDTO:
        data_source = DataSource.create(
            tenant_id=command.tenant_id,
            source_type=command.source_type,
            schema=command.schema,
            url=command.url,
        )
        await self._data_source_repository.add(data_source)
        await self._uow.commit()
        return data_source_to_dto(data_source)


__all__ = ["CreateDataSourceUseCase"]

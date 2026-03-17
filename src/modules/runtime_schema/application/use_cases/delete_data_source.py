from __future__ import annotations

from src.modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.runtime_schema.application.commands import DeleteDataSourceCommand
from src.modules.runtime_schema.application.dto import DeleteDataSourceResultDTO
from src.modules.runtime_schema.domain.errors import DataSourceNotFoundError
from src.modules.runtime_schema.domain.repositories import DataSourceRepositoryProtocol


class DeleteDataSourceUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        data_source_repository: DataSourceRepositoryProtocol,
    ):
        self._uow = uow
        self._data_source_repository = data_source_repository

    async def execute(
        self,
        command: DeleteDataSourceCommand,
    ) -> DeleteDataSourceResultDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._delete_within_transaction(command)
        return await self._delete_within_transaction(command)

    async def _delete_within_transaction(
        self,
        command: DeleteDataSourceCommand,
    ) -> DeleteDataSourceResultDTO:
        existing = await self._data_source_repository.get_by_id(command.data_source_id)
        if existing is None:
            raise DataSourceNotFoundError(command.data_source_id)

        deleted = await self._data_source_repository.delete_by_id(command.data_source_id)
        await self._uow.commit()

        return DeleteDataSourceResultDTO(
            data_source_id=command.data_source_id,
            deleted=deleted,
        )


__all__ = ["DeleteDataSourceUseCase"]

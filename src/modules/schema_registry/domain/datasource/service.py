from __future__ import annotations

from collections.abc import Callable

from src.modules.shared import ClockPort, EntityIdVO
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.repository import (
    DataSourceRepositoryProtocol,
)
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.error import (
    DataSourceAlreadyExistsError,
    DataSourceNotFoundError,
)


class DataSourceService:
    def __init__(
        self,
        repository: DataSourceRepositoryProtocol,
        clock: ClockPort,
        id_provider: Callable[[], EntityIdVO],
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._id_provider = id_provider

    async def create(
        self,
        *,
        tenant_id: EntityIdVO,
        schema_name: str,
    ) -> DataSourceEntity:
        existing = await self._repository.get_by_tenant_id(tenant_id=tenant_id)
        if existing is not None:
            raise DataSourceAlreadyExistsError(str(tenant_id))

        datasource = DataSourceEntity.create(
            id_=self._id_provider(),
            now=self._clock.now(),
            tenant_id=tenant_id,
            schema_name=SchemaNameVO(schema_name),
        )
        await self._repository.add(datasource)
        return datasource

    async def get_required_by_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> DataSourceEntity:
        datasource = await self._repository.get_by_tenant_id(tenant_id=tenant_id)
        if datasource is None:
            raise DataSourceNotFoundError(str(tenant_id))
        return datasource

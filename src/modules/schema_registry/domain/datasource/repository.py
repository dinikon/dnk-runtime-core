from typing import Protocol

from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.shared import EntityIdVO


class DataSourceRepositoryProtocol(Protocol):

    async def get_by_tenant_id(
        self, *, tenant_id: EntityIdVO
    ) -> DataSourceEntity | None: ...

    async def add(self, datasource: DataSourceEntity) -> None: ...

    async def update(self, datasource: DataSourceEntity) -> None: ...

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared import EntityIdVO
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.repository import (
    DataSourceRepositoryProtocol,
)
from src.modules.schema_registry.domain.datasource.value_object.connection_dsn import (
    ConnectionDsnVO,
)
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.datasource.value_object.type_data_source import (
    DataSourceTypeVO,
)
from src.modules.schema_registry.infrastructure.persistence.data_source import (
    DataSourceORM,
)


class SqlAlchemyDataSourceRepository(DataSourceRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_tenant_id(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> DataSourceEntity | None:
        model = await self._session.scalar(
            select(DataSourceORM)
            .where(DataSourceORM.tenant_id == tenant_id.value)
            .limit(1)
        )
        if model is None:
            return None
        return self._map_model(model)

    async def add(self, datasource: DataSourceEntity) -> None:
        self._session.add(self._to_model(datasource))
        await self._session.flush()

    async def update(self, datasource: DataSourceEntity) -> None:
        model = await self._session.get(DataSourceORM, datasource.id.value)
        if model is None:
            self._session.add(self._to_model(datasource))
        else:
            model.tenant_id = datasource.tenant_id.value
            model.data_source_type = datasource.data_source_type.value
            model.schema_name = datasource.schema_name.value
            model.connection_dsn = (
                datasource.connection_dsn.value
                if datasource.connection_dsn is not None
                else None
            )
            model.updated_at = datasource.updated_at
        await self._session.flush()

    @staticmethod
    def _to_model(datasource: DataSourceEntity) -> DataSourceORM:
        return DataSourceORM(
            id=datasource.id.value,
            created_at=datasource.created_at,
            updated_at=datasource.updated_at,
            tenant_id=datasource.tenant_id.value,
            data_source_type=datasource.data_source_type.value,
            schema_name=datasource.schema_name.value,
            connection_dsn=(
                datasource.connection_dsn.value
                if datasource.connection_dsn is not None
                else None
            ),
        )

    @staticmethod
    def _map_model(model: DataSourceORM) -> DataSourceEntity:
        return DataSourceEntity(
            id=EntityIdVO.from_value(model.id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            tenant_id=EntityIdVO.from_value(model.tenant_id),
            data_source_type=DataSourceTypeVO(model.data_source_type),
            schema_name=SchemaNameVO(model.schema_name),
            connection_dsn=(
                ConnectionDsnVO(model.connection_dsn)
                if model.connection_dsn is not None
                else None
            ),
        )

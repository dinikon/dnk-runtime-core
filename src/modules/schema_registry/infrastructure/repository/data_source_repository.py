from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.repository import (
    DataSourceRepositoryProtocol,
)
from src.modules.schema_registry.domain.datasource.value_object.connection_dsn import (
    ConnectionDsnVO,
)
from src.modules.schema_registry.domain.datasource.value_object.data_source_id import (
    DataSourceIdVO,
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
from src.modules.shared import EntityIdVO

class SqlAlchemyDataSourceRepository(DataSourceRepositoryProtocol):
    """SQLAlchemy-репозиторий datasource metadata."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует репозиторий текущей async-сессией."""
        self._session = session

    async def get_by_tenant_id(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> DataSourceEntity | None:
        """Ищет datasource metadata по tenant_id."""
        model = await self._session.scalar(
            select(DataSourceORM)
            .where(DataSourceORM.tenant_id == tenant_id.uuid)
            .limit(1)
        )
        if model is None:
            return None
        return self._map_model(model)

    async def add(self, datasource: DataSourceEntity) -> None:
        """Добавляет datasource model и flush-ит сессию."""
        self._session.add(self._to_model(datasource))
        await self._session.flush()

    async def update(self, datasource: DataSourceEntity) -> None:
        """Обновляет существующий datasource или добавляет новый, если model нет."""
        model = await self._session.get(DataSourceORM, datasource.id.uuid)
        if model is None:
            self._session.add(self._to_model(datasource))
        else:
            model.tenant_id = datasource.tenant_id.uuid
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
        """Мапит доменную datasource entity в SQLAlchemy-модель."""
        return DataSourceORM(
            id=datasource.id.uuid,
            created_at=datasource.created_at,
            updated_at=datasource.updated_at,
            tenant_id=datasource.tenant_id.uuid,
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
        """Мапит SQLAlchemy-модель datasource в доменную entity."""
        return DataSourceEntity(
            id=DataSourceIdVO.from_value(model.id),
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

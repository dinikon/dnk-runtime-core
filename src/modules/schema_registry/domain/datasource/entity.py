from dataclasses import dataclass
from datetime import datetime
from typing import Self

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
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class DataSourceEntity:
    """Доменная сущность источника данных, привязанного к tenant runtime-схеме."""

    id: DataSourceIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO

    data_source_type: DataSourceTypeVO
    schema_name: SchemaNameVO
    connection_dsn: ConnectionDsnVO | None

    @classmethod
    def create(
        cls,
        *,
        id_: DataSourceIdVO,
        now: datetime,
        tenant_id: EntityIdVO,
        schema_name: SchemaNameVO,
        connection_dsn: ConnectionDsnVO | None = None,
        data_source_type: DataSourceTypeVO = DataSourceTypeVO.POSTGRES,
    ) -> Self:
        """Создает datasource с едиными created_at/updated_at и PostgreSQL default."""
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            data_source_type=data_source_type,
            schema_name=schema_name,
            connection_dsn=connection_dsn,
        )

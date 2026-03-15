from __future__ import annotations

from src.modules.runtime_schema.application.schema.dto import (
    CreateSchemaCommandDTO,
    CreateSchemaResultDTO,
)
from src.modules.runtime_schema.application.schema.ports import (
    CreateSchemaUseCaseProtocol,
    DataSourceWriteRepositoryProtocol,
    DatabaseSchemaRepositoryProtocol,
)
from src.modules.runtime_schema.domain.schema import (
    DataSourceEntity,
    InvalidSchemaTypeError,
    SchemaIdVO,
    SchemaNameVO,
    SchemaTypeVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.kernel.time.ports import ClockPort


class CreateSchemaUseCase(CreateSchemaUseCaseProtocol):
    def __init__(
        self,
        data_source_repository: DataSourceWriteRepositoryProtocol,
        database_schema_repository: DatabaseSchemaRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._data_source_repository = data_source_repository
        self._database_schema_repository = database_schema_repository
        self._clock = clock

    async def execute(self, dto: CreateSchemaCommandDTO) -> CreateSchemaResultDTO:
        schema_id = (
            SchemaIdVO.from_value(dto.schema_id)
            if dto.schema_id is not None
            else SchemaIdVO()
        )
        tenant_id = EntityIdVO.from_value(dto.tenant_id)
        try:
            schema_type = SchemaTypeVO(dto.schema_type)
        except ValueError:
            raise InvalidSchemaTypeError(dto.schema_type) from None
        schema_name = SchemaNameVO(dto.schema_name)
        now = self._clock.now()

        entity = DataSourceEntity.create(
            id=schema_id,
            tenant_id=tenant_id,
            type=schema_type,
            schema_name=schema_name,
            now=now,
        )

        await self._database_schema_repository.create_schema(str(schema_name))
        created_entity = await self._data_source_repository.add(entity)

        return CreateSchemaResultDTO(
            schema_id=str(created_entity.id),
            tenant_id=str(created_entity.tenant_id),
            schema_name=str(created_entity.schema_name),
            schema_type=created_entity.type.value,
            created_at=created_entity.created_at,
            updated_at=created_entity.updated_at,
        )


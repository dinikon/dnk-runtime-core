from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from modules.schema_registry.domain.datasource.repository import (
    DataSourceRepositoryProtocol,
)
from modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from modules.shared import ClockPort, EntityIdVO
from src.modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.schema_registry.application.ports.seed_reader import SeedReaderPort
from src.modules.schema_registry.application.ports.tenant_schema_executor import (
    TenantSchemaExecutorPort,
)
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.migration.diff_service import SchemaDiffService
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)


@dataclass(slots=True, frozen=True)
class CreateSchemaCommand:
    tenant_id: UUID
    schema_name: str
    seed_path: str


class CreateSchemaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        seed_reader: SeedReaderPort,
        schema_diff_service: SchemaDiffService,
        schema_executor: TenantSchemaExecutorPort,
        now_provider: ClockPort,
        id_provider,
        checksum_service,
        datasource_repository: DataSourceRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._seed_reader = seed_reader
        self._schema_diff_service = schema_diff_service
        self._schema_executor = schema_executor
        self._now_provider = now_provider
        self._id_provider = id_provider
        self._checksum_service = checksum_service
        self.datasource_repository = datasource_repository

    async def execute(self, command: CreateSchemaCommand) -> None:
        now: datetime = self._now_provider.now()
        seed = await self._seed_reader.read(seed_path=command.seed_path)
        checksum = self._checksum_service.calculate(seed)

        async with self._uow:
            existing = await self.datasource_repository.get_by_tenant_id(
                tenant_id=EntityIdVO(command.tenant_id)
            )
            if existing is not None:
                raise ValueError(
                    "Schema registry datasource already exists for tenant."
                )

            datasource = DataSourceEntity.create(
                id_=self._id_provider(),
                tenant_id=EntityIdVO(command.tenant_id),
                now=now,
                schema_name=SchemaNameVO(command.schema_name),
            )

            plan = self._schema_diff_service.build_create_plan(
                schema_name=command.schema_name,
                seed=seed,
            )

            await self._schema_executor.execute(plan=plan)

            objects = []
            for object_seed in seed.objects:
                object_entity = ObjectEntity.create(
                    id_=self._id_provider(),
                    tenant_id=command.tenant_id,
                    now=now,
                    object_name=ObjectNameVO.from_raw(object_seed.name),
                    object_label=ObjectLabelVO.from_raw(object_seed.label),
                    description=object_seed.description,
                )

                for field_seed in object_seed.fields:
                    object_entity.add_field(
                        field_id=self._id_provider(),
                        now=now,
                        field_name=field_seed.name,
                        field_type=field_seed.type,  # позже сюда маппер в FieldTypeVO
                        label=field_seed.label,
                        description=field_seed.description,
                        is_nullable=field_seed.is_nullable,
                        options=field_seed.options,
                        settings=field_seed.settings,
                    )

                objects.append(object_entity)

            await self._uow.datasource_repository.add(datasource)
            await self._uow.object_repository.replace_all_for_tenant(
                tenant_id=command.tenant_id,
                objects=objects,
            )

            await self._uow.commit()

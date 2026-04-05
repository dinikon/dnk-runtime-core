import uuid6

from modules.schema_registry.application.ports.seed_reader import SeedReaderPort
from modules.schema_registry.application.ports.tenant_schema_executor import (
    TenantSchemaExecutorPort,
)
from modules.schema_registry.application.ports.tenant_schema_inspector import (
    TenantSchemaInspectorPort,
)
from modules.schema_registry.domain.migration.diff_service import SchemaDiffService
from modules.schema_registry.domain.object.entity import ObjectEntity
from modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from modules.schema_registry.domain.object.value_object.object_name import ObjectNameVO
from modules.shared import ClockPort, EntityIdVO
from modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.schema_registry.application.command.diff_schema_command import (
    DiffSchemaCommand,
)


class DiffSchemaUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        seed_reader: SeedReaderPort,
        inspector: TenantSchemaInspectorPort,
        schema_diff_service: SchemaDiffService,
        schema_executor: TenantSchemaExecutorPort,
        now_provider: ClockPort,
        checksum_service,
    ) -> None:
        self._uow = uow
        self._seed_reader = seed_reader
        self._inspector = inspector
        self._schema_diff_service = schema_diff_service
        self._schema_executor = schema_executor
        self._now_provider = now_provider
        self._checksum_service = checksum_service

    async def execute(self, command: DiffSchemaCommand) -> None:
        now = self._now_provider.now()
        seed = await self._seed_reader.read(seed_path=command.seed_path)
        checksum = self._checksum_service.calculate(seed)

        async with self._uow:
            datasource = await self._uow.datasource_repository.get_by_tenant_id(
                tenant_id=command.tenant_id
            )
            if datasource is None:
                raise ValueError("Datasource for tenant not found.")

            actual_schema = await self._inspector.inspect(
                schema_name=datasource.schema_name
            )

            plan = self._schema_diff_service.build_diff_plan(
                schema_name=datasource.schema_name,
                seed=seed,
                actual_schema=actual_schema,
            )

            if not plan.is_empty:
                await self._schema_executor.execute(plan=plan)

            datasource.update_seed_state(
                now=now,
                seed_checksum=checksum,
                seed_version=seed.version,
            )

            objects = []
            for object_seed in seed.objects:
                object_entity = ObjectEntity.create(
                    id_=EntityIdVO(value=uuid6.uuid7()),
                    tenant_id=command.tenant_id,
                    now=now,
                    object_name=ObjectNameVO(
                        plural=object_seed.name, singular=object_seed.name + "s"
                    ),
                    object_label=ObjectLabelVO(
                        plural=object_seed.label, singular=object_seed.label + "s"
                    ),
                    description=object_seed.description,
                )

                for field_seed in object_seed.fields:
                    object_entity.add_field(
                        field_id=EntityIdVO(value=uuid6.uuid7()),
                        now=now,
                        field_name=field_seed.name,
                        field_type=field_seed.type,
                        label=field_seed.label,
                        description=field_seed.description,
                        is_nullable=field_seed.is_nullable,
                        options=field_seed.options,
                        settings=field_seed.settings,
                    )

                objects.append(object_entity)

            await self._uow.datasource_repository.update(datasource)
            await self._uow.object_repository.replace_all_for_tenant(
                tenant_id=command.tenant_id,
                objects=objects,
            )

            await self._uow.commit()

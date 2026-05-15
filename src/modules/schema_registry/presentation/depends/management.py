from __future__ import annotations

from src.modules.shared.kernel.time.ports import ClockPort
from src.modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.schema_registry.application.use_case.diff_schema_use_case import (
    DiffSchemaUseCase,
)
from src.modules.schema_registry.presentation.depends.application import (
    get_diff_schema_use_case,
    get_postgres_schema_plan_service,
    get_postgres_schema_service,
    get_schema_registry_metadata_read_service,
    get_schema_registry_metadata_write_service,
    get_schema_seed_service,
)
from src.modules.schema_registry.presentation.depends.infrastructure import (
    get_data_source_repository,
    get_data_source_service,
    get_field_type_catalog,
    get_object_repository,
    get_object_service,
    get_postgres_field_canonicalizer,
    get_relation_repository,
    get_relation_service,
    get_schema_seed_reader,
    get_tenant_schema_executor,
    get_tenant_schema_inspector,
)

def build_diff_schema_use_case(
    *,
    uow: UnitOfWorkProtocol,
    clock: ClockPort,
) -> DiffSchemaUseCase:
    """Собирает DiffSchemaUseCase вне FastAPI DI для management-команд."""
    field_type_catalog = get_field_type_catalog()
    postgres_field_canonicalizer = get_postgres_field_canonicalizer()
    data_source_repository = get_data_source_repository(uow)
    object_repository = get_object_repository(uow)
    relation_repository = get_relation_repository(uow)
    data_source_service = get_data_source_service(
        repository=data_source_repository,
        clock=clock,
    )
    object_service = get_object_service(
        repository=object_repository,
        clock=clock,
        field_type_catalog=field_type_catalog,
    )
    relation_service = get_relation_service(
        repository=relation_repository,
        clock=clock,
    )
    schema_seed_service = get_schema_seed_service(
        seed_reader=get_schema_seed_reader(),
        field_type_catalog=field_type_catalog,
    )
    postgres_schema_service = get_postgres_schema_service(
        inspector=get_tenant_schema_inspector(uow, postgres_field_canonicalizer),
        executor=get_tenant_schema_executor(uow, postgres_field_canonicalizer),
    )
    return get_diff_schema_use_case(
        schema_seed_service=schema_seed_service,
        schema_registry_metadata_read_service=get_schema_registry_metadata_read_service(
            data_source_service=data_source_service,
            object_service=object_service,
            relation_service=relation_service,
        ),
        schema_plan_service=get_postgres_schema_plan_service(
            field_type_catalog=field_type_catalog,
            postgres_field_canonicalizer=postgres_field_canonicalizer,
        ),
        postgres_schema_service=postgres_schema_service,
        schema_registry_metadata_write_service=get_schema_registry_metadata_write_service(
            data_source_service=data_source_service,
            object_service=object_service,
            relation_service=relation_service,
        ),
    )


__all__ = [
    "build_diff_schema_use_case",
]

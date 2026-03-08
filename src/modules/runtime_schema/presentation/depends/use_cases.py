from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.use_case import (
    BootstrapTenantSystemSchemaUseCase,
)
from src.modules.runtime_schema.infrastructure.schema_manager import (
    SqlAlchemyTenantSchemaManager,
)
from src.modules.runtime_schema.infrastructure.system_definitions import (
    StaticSystemObjectDefinitionsProvider,
)
from src.modules.runtime_schema.presentation.depends.repositories import (
    FieldMetadataRepositoryDep,
    ObjectMetadataRepositoryDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_bootstrap_tenant_system_schema_use_case(
    uow: UoWDep,
    object_metadata_repository: ObjectMetadataRepositoryDep,
    field_metadata_repository: FieldMetadataRepositoryDep,
) -> BootstrapTenantSystemSchemaUseCase:
    return BootstrapTenantSystemSchemaUseCase(
        object_metadata_repository=object_metadata_repository,
        field_metadata_repository=field_metadata_repository,
        system_object_definitions_provider=StaticSystemObjectDefinitionsProvider(),
        tenant_schema_manager=SqlAlchemyTenantSchemaManager(uow.session),
    )


BootstrapTenantSystemSchemaUseCaseDep = Annotated[
    BootstrapTenantSystemSchemaUseCase,
    Depends(get_bootstrap_tenant_system_schema_use_case),
]

__all__ = [
    "get_bootstrap_tenant_system_schema_use_case",
    "BootstrapTenantSystemSchemaUseCaseDep",
]

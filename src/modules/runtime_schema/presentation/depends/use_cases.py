from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.use_case import (
    BootstrapTenantSystemSchemaUseCase,
)
from src.modules.runtime_schema.application.relations.use_cases.create_relation import (
    CreateRelationUseCase,
)
from src.modules.runtime_schema.application.relations.use_cases.delete_relation import (
    DeleteRelationUseCase,
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
    RelationMetadataRepositoryDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_bootstrap_tenant_system_schema_use_case(
    uow: UoWDep,
    object_metadata_repository: ObjectMetadataRepositoryDep,
    field_metadata_repository: FieldMetadataRepositoryDep,
    relation_metadata_repository: RelationMetadataRepositoryDep,
) -> BootstrapTenantSystemSchemaUseCase:
    return BootstrapTenantSystemSchemaUseCase(
        object_metadata_repository=object_metadata_repository,
        field_metadata_repository=field_metadata_repository,
        relation_metadata_repository=relation_metadata_repository,
        system_object_definitions_provider=StaticSystemObjectDefinitionsProvider(),
        tenant_schema_manager=SqlAlchemyTenantSchemaManager(uow.session),
    )


BootstrapTenantSystemSchemaUseCaseDep = Annotated[
    BootstrapTenantSystemSchemaUseCase,
    Depends(get_bootstrap_tenant_system_schema_use_case),
]


def get_create_relation_use_case(
    uow: UoWDep,
    object_metadata_repository: ObjectMetadataRepositoryDep,
    field_metadata_repository: FieldMetadataRepositoryDep,
    relation_metadata_repository: RelationMetadataRepositoryDep,
) -> CreateRelationUseCase:
    return CreateRelationUseCase(
        objects_repository=object_metadata_repository,
        fields_repository=field_metadata_repository,
        relations_repository=relation_metadata_repository,
        schema_manager=SqlAlchemyTenantSchemaManager(uow.session),
    )


CreateRelationUseCaseDep = Annotated[
    CreateRelationUseCase,
    Depends(get_create_relation_use_case),
]


def get_delete_relation_use_case(
    uow: UoWDep,
    object_metadata_repository: ObjectMetadataRepositoryDep,
    field_metadata_repository: FieldMetadataRepositoryDep,
    relation_metadata_repository: RelationMetadataRepositoryDep,
) -> DeleteRelationUseCase:
    return DeleteRelationUseCase(
        objects_repository=object_metadata_repository,
        fields_repository=field_metadata_repository,
        relations_repository=relation_metadata_repository,
        schema_manager=SqlAlchemyTenantSchemaManager(uow.session),
    )


DeleteRelationUseCaseDep = Annotated[
    DeleteRelationUseCase,
    Depends(get_delete_relation_use_case),
]

__all__ = [
    "get_bootstrap_tenant_system_schema_use_case",
    "BootstrapTenantSystemSchemaUseCaseDep",
    "get_create_relation_use_case",
    "CreateRelationUseCaseDep",
    "get_delete_relation_use_case",
    "DeleteRelationUseCaseDep",
]

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from src.modules.crm.domain.repositories import (
    CompanyRepositoryProtocol,
    ContactRepositoryProtocol,
)
from src.modules.crm.infrastructure.repositories import (
    SqlAlchemyCompanyRepository,
    SqlAlchemyContactRepository,
)
from src.modules.runtime_record.application import RuntimeRecordApplicationService
from src.modules.runtime_record.domain.repositories import RuntimeValueRepositoryProtocol
from src.modules.runtime_record.infrastructure import SqlAlchemyRuntimeValueRepository
from src.modules.runtime_schema.domain.repositories import (
    DataSourceRepositoryProtocol,
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.depends.uow import UoWDep


async def get_tenant_schema_name(tenant_id: UUID, uow: UoWDep) -> str:
    data_source_repository = SqlAlchemyDataSourceRepository(uow.session)
    data_sources = await data_source_repository.list_by_tenant_id(tenant_id)
    if not data_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runtime data source for tenant '{tenant_id}' was not found.",
        )
    return data_sources[0].schema


CrmTenantSchemaNameDep = Annotated[
    str,
    Depends(get_tenant_schema_name),
]


def get_contact_repository(
    uow: UoWDep,
    schema_name: CrmTenantSchemaNameDep,
) -> ContactRepositoryProtocol:
    return SqlAlchemyContactRepository(uow.session, schema_name=schema_name)


ContactRepositoryDep = Annotated[
    ContactRepositoryProtocol,
    Depends(get_contact_repository),
]


def get_company_repository(
    uow: UoWDep,
    schema_name: CrmTenantSchemaNameDep,
) -> CompanyRepositoryProtocol:
    return SqlAlchemyCompanyRepository(uow.session, schema_name=schema_name)


CompanyRepositoryDep = Annotated[
    CompanyRepositoryProtocol,
    Depends(get_company_repository),
]


def get_data_source_repository(uow: UoWDep) -> DataSourceRepositoryProtocol:
    return SqlAlchemyDataSourceRepository(uow.session)


def get_object_metadata_repository(uow: UoWDep) -> ObjectMetadataRepositoryProtocol:
    return SqlAlchemyObjectMetadataRepository(uow.session)


def get_field_metadata_repository(uow: UoWDep) -> FieldMetadataRepositoryProtocol:
    return SqlAlchemyFieldMetadataRepository(uow.session)


def get_runtime_value_repository(uow: UoWDep) -> RuntimeValueRepositoryProtocol:
    return SqlAlchemyRuntimeValueRepository(uow.session)


def get_runtime_record_service(
    uow: UoWDep,
    object_metadata_repository: Annotated[
        ObjectMetadataRepositoryProtocol,
        Depends(get_object_metadata_repository),
    ],
    field_metadata_repository: Annotated[
        FieldMetadataRepositoryProtocol,
        Depends(get_field_metadata_repository),
    ],
    data_source_repository: Annotated[
        DataSourceRepositoryProtocol,
        Depends(get_data_source_repository),
    ],
    runtime_value_repository: Annotated[
        RuntimeValueRepositoryProtocol,
        Depends(get_runtime_value_repository),
    ],
) -> RuntimeRecordApplicationService:
    return RuntimeRecordApplicationService(
        uow=uow,
        object_metadata_repository=object_metadata_repository,
        field_metadata_repository=field_metadata_repository,
        data_source_repository=data_source_repository,
        runtime_value_repository=runtime_value_repository,
    )


RuntimeRecordServiceDep = Annotated[
    RuntimeRecordApplicationService,
    Depends(get_runtime_record_service),
]


__all__ = [
    "CompanyRepositoryDep",
    "ContactRepositoryDep",
    "CrmTenantSchemaNameDep",
    "RuntimeRecordServiceDep",
    "get_company_repository",
    "get_contact_repository",
    "get_data_source_repository",
    "get_field_metadata_repository",
    "get_object_metadata_repository",
    "get_runtime_record_service",
    "get_runtime_value_repository",
    "get_tenant_schema_name",
]

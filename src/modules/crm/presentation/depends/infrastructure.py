from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.company.query.describe_company_fields_repository import (
    CompanyFieldsDescriptionRepositoryProtocol,
)
from src.modules.crm.application.company.query.repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.application.contact.query.describe_contact_fields_repository import (
    ContactFieldsDescriptionRepositoryProtocol,
)
from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.domain.company.repository import (
    CompanyCommandRepositoryProtocol,
)
from src.modules.crm.domain.contact.repository import (
    ContactCommandRepositoryProtocol,
)
from src.modules.crm.infrastructure import (
    CompanyModelDescriptionRepository,
    CompanyRuntimeRepository,
    ContactModelDescriptionRepository,
    ContactRuntimeRepository,
)
from src.modules.runtime_data import (
    PostgresRuntimeGateway,
    QueryCapabilityResolver,
    RuntimeFieldTypePolicy,
)
from src.modules.runtime_data.application.query import RuntimeObjectQueryService
from src.modules.schema_registry.presentation.depends.application import (
    DescribeRuntimeObjectUseCaseDep,
    RuntimeObjectResolverDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    """Создает policy приведения runtime field-типов для CRM gateway."""

    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_runtime_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
) -> PostgresRuntimeGateway:
    """Создает PostgreSQL runtime gateway на базе текущей UoW-сессии."""
    return PostgresRuntimeGateway(
        uow.session,
        type_policy=type_policy,
    )


RuntimeGatewayDep = Annotated[
    PostgresRuntimeGateway,
    Depends(get_runtime_gateway),
]


def get_runtime_object_query_service(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> RuntimeObjectQueryService:
    """Создает application service runtime search для CRM read paths."""
    return RuntimeObjectQueryService(
        runtime_object_resolver=runtime_object_resolver,
        runtime_query_gateway=runtime_gateway,
    )


RuntimeObjectQueryServiceDep = Annotated[
    RuntimeObjectQueryService,
    Depends(get_runtime_object_query_service),
]


def get_query_capability_resolver() -> QueryCapabilityResolver:
    """Creates runtime query capability resolver for metadata endpoints."""
    return QueryCapabilityResolver()


QueryCapabilityResolverDep = Annotated[
    QueryCapabilityResolver,
    Depends(get_query_capability_resolver),
]


def get_contact_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> ContactQueryRepositoryProtocol:
    """Создает query repository контактов поверх runtime gateway."""
    return ContactRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


ContactQueryRepositoryDep = Annotated[
    ContactQueryRepositoryProtocol,
    Depends(get_contact_query_repository),
]


def get_contact_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> ContactCommandRepositoryProtocol:
    """Создает command repository контактов поверх runtime gateway."""
    return ContactRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


ContactCommandRepositoryDep = Annotated[
    ContactCommandRepositoryProtocol,
    Depends(get_contact_command_repository),
]


def get_company_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> CompanyQueryRepositoryProtocol:
    """Создает query repository компаний поверх runtime gateway."""
    return CompanyRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


CompanyQueryRepositoryDep = Annotated[
    CompanyQueryRepositoryProtocol,
    Depends(get_company_query_repository),
]


def get_company_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> CompanyCommandRepositoryProtocol:
    """Создает command repository компаний поверх runtime gateway."""
    return CompanyRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


CompanyCommandRepositoryDep = Annotated[
    CompanyCommandRepositoryProtocol,
    Depends(get_company_command_repository),
]


def get_contact_fields_description_repository(
    describe_runtime_object_use_case: DescribeRuntimeObjectUseCaseDep,
    runtime_object_resolver: RuntimeObjectResolverDep,
    query_capability_resolver: QueryCapabilityResolverDep,
) -> ContactFieldsDescriptionRepositoryProtocol:
    """Создает repository описания модели contact через schema_registry."""
    return ContactModelDescriptionRepository(
        describe_runtime_object_use_case=describe_runtime_object_use_case,
        runtime_object_resolver=runtime_object_resolver,
        query_capability_resolver=query_capability_resolver,
    )


ContactFieldsDescriptionRepositoryDep = Annotated[
    ContactFieldsDescriptionRepositoryProtocol,
    Depends(get_contact_fields_description_repository),
]


def get_company_fields_description_repository(
    describe_runtime_object_use_case: DescribeRuntimeObjectUseCaseDep,
) -> CompanyFieldsDescriptionRepositoryProtocol:
    """Создает repository описания модели company через schema_registry."""
    return CompanyModelDescriptionRepository(
        describe_runtime_object_use_case=describe_runtime_object_use_case,
    )


CompanyFieldsDescriptionRepositoryDep = Annotated[
    CompanyFieldsDescriptionRepositoryProtocol,
    Depends(get_company_fields_description_repository),
]


__all__ = [
    "CompanyCommandRepositoryDep",
    "CompanyFieldsDescriptionRepositoryDep",
    "CompanyQueryRepositoryDep",
    "ContactCommandRepositoryDep",
    "ContactFieldsDescriptionRepositoryDep",
    "ContactQueryRepositoryDep",
    "QueryCapabilityResolverDep",
    "RuntimeGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeObjectQueryServiceDep",
    "get_company_command_repository",
    "get_company_fields_description_repository",
    "get_company_query_repository",
    "get_contact_command_repository",
    "get_contact_fields_description_repository",
    "get_contact_query_repository",
    "get_query_capability_resolver",
    "get_runtime_field_type_policy",
    "get_runtime_gateway",
    "get_runtime_object_query_service",
]

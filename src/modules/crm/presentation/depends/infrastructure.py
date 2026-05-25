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
from src.modules.runtime_data.application.query.capabilities.query_capability_resolver import (
    QueryCapabilityResolver,
)
from src.modules.runtime_data.application.query.runtime_object_query_service import (
    RuntimeObjectQueryService,
)
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.command_gateway import (
    PostgresRuntimeCommandGateway,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.query_gateway import (
    PostgresRuntimeQueryGateway,
)
from src.modules.schema_registry.presentation.depends.application import (
    DescribeRuntimeObjectUseCaseDep,
    RuntimeObjectResolverDep,
)
from src.modules.shared.application.events import OutboxRepositoryProtocol
from src.modules.shared.presentation.events import build_outbox_repository
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    """Создает policy приведения runtime field-типов для CRM gateway."""

    return RuntimeFieldTypePolicy()


RuntimeFieldTypePolicyDep = Annotated[
    RuntimeFieldTypePolicy,
    Depends(get_runtime_field_type_policy),
]


def get_runtime_query_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
) -> PostgresRuntimeQueryGateway:
    """Создает PostgreSQL runtime query gateway на базе текущей UoW-сессии."""
    return PostgresRuntimeQueryGateway(
        uow.session,
        type_policy=type_policy,
    )


RuntimeQueryGatewayDep = Annotated[
    PostgresRuntimeQueryGateway,
    Depends(get_runtime_query_gateway),
]


def get_runtime_command_gateway(
    uow: UoWDep,
    type_policy: RuntimeFieldTypePolicyDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> PostgresRuntimeCommandGateway:
    """Создает PostgreSQL runtime command gateway на базе текущей UoW-сессии."""
    return PostgresRuntimeCommandGateway(
        uow.session,
        type_policy=type_policy,
        query_gateway=runtime_query_gateway,
    )


RuntimeCommandGatewayDep = Annotated[
    PostgresRuntimeCommandGateway,
    Depends(get_runtime_command_gateway),
]


def get_outbox_repository(uow: UoWDep) -> OutboxRepositoryProtocol:
    """Создает shared integration outbox repository в текущей UoW session."""
    return build_outbox_repository(uow.session)


OutboxRepositoryDep = Annotated[
    OutboxRepositoryProtocol,
    Depends(get_outbox_repository),
]


def get_runtime_object_query_service(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> RuntimeObjectQueryService:
    """Создает application service runtime search для CRM read paths."""
    return RuntimeObjectQueryService(
        runtime_object_resolver=runtime_object_resolver,
        runtime_query_gateway=runtime_query_gateway,
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
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> ContactQueryRepositoryProtocol:
    """Создает query repository контактов поверх runtime gateway."""
    return ContactRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


ContactQueryRepositoryDep = Annotated[
    ContactQueryRepositoryProtocol,
    Depends(get_contact_query_repository),
]


def get_contact_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> ContactCommandRepositoryProtocol:
    """Создает command repository контактов поверх runtime gateway."""
    return ContactRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


ContactCommandRepositoryDep = Annotated[
    ContactCommandRepositoryProtocol,
    Depends(get_contact_command_repository),
]


def get_company_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> CompanyQueryRepositoryProtocol:
    """Создает query repository компаний поверх runtime gateway."""
    return CompanyRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


CompanyQueryRepositoryDep = Annotated[
    CompanyQueryRepositoryProtocol,
    Depends(get_company_query_repository),
]


def get_company_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> CompanyCommandRepositoryProtocol:
    """Создает command repository компаний поверх runtime gateway."""
    return CompanyRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
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
    "OutboxRepositoryDep",
    "QueryCapabilityResolverDep",
    "RuntimeCommandGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeObjectQueryServiceDep",
    "RuntimeQueryGatewayDep",
    "get_company_command_repository",
    "get_company_fields_description_repository",
    "get_company_query_repository",
    "get_contact_command_repository",
    "get_contact_fields_description_repository",
    "get_contact_query_repository",
    "get_outbox_repository",
    "get_query_capability_resolver",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
    "get_runtime_object_query_service",
]

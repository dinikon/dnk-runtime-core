from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.inventory.application.category.query.describe_category_fields_repository import (
    CategoryFieldsDescriptionRepositoryProtocol,
)
from src.modules.inventory.application.category.query.repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.inventory.application.product.query.describe_product_fields_repository import (
    ProductFieldsDescriptionRepositoryProtocol,
)
from src.modules.inventory.application.product.query.repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.inventory.domain.category.repository import (
    CategoryCommandRepositoryProtocol,
)
from src.modules.inventory.domain.product.repository import (
    ProductCommandRepositoryProtocol,
)
from src.modules.inventory.infrastructure import (
    CategoryModelDescriptionRepository,
    CategoryRuntimeRepository,
    ProductModelDescriptionRepository,
    ProductRuntimeRepository,
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
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    """Создает policy приведения runtime field-типов для inventory gateway."""
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


def get_product_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> ProductQueryRepositoryProtocol:
    """Создает query repository товаров поверх runtime gateway."""
    return ProductRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


ProductQueryRepositoryDep = Annotated[
    ProductQueryRepositoryProtocol,
    Depends(get_product_query_repository),
]


def get_product_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> ProductCommandRepositoryProtocol:
    """Создает command repository товаров поверх runtime gateway."""
    return ProductRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


ProductCommandRepositoryDep = Annotated[
    ProductCommandRepositoryProtocol,
    Depends(get_product_command_repository),
]


def get_category_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> CategoryQueryRepositoryProtocol:
    """Создает query repository категорий поверх runtime gateway."""
    return CategoryRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


CategoryQueryRepositoryDep = Annotated[
    CategoryQueryRepositoryProtocol,
    Depends(get_category_query_repository),
]


def get_category_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_command_gateway: RuntimeCommandGatewayDep,
    runtime_query_gateway: RuntimeQueryGatewayDep,
) -> CategoryCommandRepositoryProtocol:
    """Создает command repository категорий поверх runtime gateway."""
    return CategoryRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_command_gateway,
        runtime_query_gateway=runtime_query_gateway,
    )


CategoryCommandRepositoryDep = Annotated[
    CategoryCommandRepositoryProtocol,
    Depends(get_category_command_repository),
]


def get_product_fields_description_repository(
    describe_runtime_object_use_case: DescribeRuntimeObjectUseCaseDep,
) -> ProductFieldsDescriptionRepositoryProtocol:
    """Создает repository описания модели product через schema_registry."""
    return ProductModelDescriptionRepository(
        describe_runtime_object_use_case=describe_runtime_object_use_case,
    )


ProductFieldsDescriptionRepositoryDep = Annotated[
    ProductFieldsDescriptionRepositoryProtocol,
    Depends(get_product_fields_description_repository),
]


def get_category_fields_description_repository(
    describe_runtime_object_use_case: DescribeRuntimeObjectUseCaseDep,
) -> CategoryFieldsDescriptionRepositoryProtocol:
    """Создает repository описания модели product_category через schema_registry."""
    return CategoryModelDescriptionRepository(
        describe_runtime_object_use_case=describe_runtime_object_use_case,
    )


CategoryFieldsDescriptionRepositoryDep = Annotated[
    CategoryFieldsDescriptionRepositoryProtocol,
    Depends(get_category_fields_description_repository),
]

__all__ = [
    "CategoryCommandRepositoryDep",
    "CategoryFieldsDescriptionRepositoryDep",
    "CategoryQueryRepositoryDep",
    "ProductCommandRepositoryDep",
    "ProductFieldsDescriptionRepositoryDep",
    "ProductQueryRepositoryDep",
    "RuntimeCommandGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "RuntimeQueryGatewayDep",
    "get_category_command_repository",
    "get_category_fields_description_repository",
    "get_category_query_repository",
    "get_product_command_repository",
    "get_product_fields_description_repository",
    "get_product_query_repository",
    "get_runtime_command_gateway",
    "get_runtime_field_type_policy",
    "get_runtime_query_gateway",
]

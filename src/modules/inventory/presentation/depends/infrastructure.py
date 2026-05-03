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
from src.modules.runtime_data import PostgresRuntimeGateway, RuntimeFieldTypePolicy
from src.modules.schema_registry.presentation.depends.application import (
    DescribeRuntimeObjectUseCaseDep,
    RuntimeObjectResolverDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_runtime_field_type_policy() -> RuntimeFieldTypePolicy:
    """Создает policy приведения runtime field-типов для inventory gateway."""
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


def get_product_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> ProductQueryRepositoryProtocol:
    """Создает query repository товаров поверх runtime gateway."""
    return ProductRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


ProductQueryRepositoryDep = Annotated[
    ProductQueryRepositoryProtocol,
    Depends(get_product_query_repository),
]


def get_product_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> ProductCommandRepositoryProtocol:
    """Создает command repository товаров поверх runtime gateway."""
    return ProductRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


ProductCommandRepositoryDep = Annotated[
    ProductCommandRepositoryProtocol,
    Depends(get_product_command_repository),
]


def get_category_query_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> CategoryQueryRepositoryProtocol:
    """Создает query repository категорий поверх runtime gateway."""
    return CategoryRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
    )


CategoryQueryRepositoryDep = Annotated[
    CategoryQueryRepositoryProtocol,
    Depends(get_category_query_repository),
]


def get_category_command_repository(
    runtime_object_resolver: RuntimeObjectResolverDep,
    runtime_gateway: RuntimeGatewayDep,
) -> CategoryCommandRepositoryProtocol:
    """Создает command repository категорий поверх runtime gateway."""
    return CategoryRuntimeRepository(
        runtime_object_resolver=runtime_object_resolver,
        runtime_command_gateway=runtime_gateway,
        runtime_query_gateway=runtime_gateway,
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
    "RuntimeGatewayDep",
    "RuntimeFieldTypePolicyDep",
    "get_category_command_repository",
    "get_category_fields_description_repository",
    "get_category_query_repository",
    "get_product_command_repository",
    "get_product_fields_description_repository",
    "get_product_query_repository",
    "get_runtime_field_type_policy",
    "get_runtime_gateway",
]

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.inventory.application.category.use_case import (
    CreateCategoryUseCase,
    DeleteCategoryUseCase,
    DescribeCategoryFieldsUseCase,
    GetCategoryUseCase,
    ListCategoriesUseCase,
    UpdateCategoryUseCase,
)
from src.modules.inventory.application.product.use_case import (
    CreateProductUseCase,
    DeleteProductUseCase,
    DescribeProductFieldsUseCase,
    GetProductUseCase,
    ListProductsUseCase,
    UpdateProductUseCase,
)
from src.modules.inventory.domain.category.service import CategoryService
from src.modules.inventory.domain.product.service import ProductService
from src.modules.inventory.presentation.depends.infrastructure import (
    CategoryCommandRepositoryDep,
    CategoryFieldsDescriptionRepositoryDep,
    CategoryQueryRepositoryDep,
    ProductCommandRepositoryDep,
    ProductFieldsDescriptionRepositoryDep,
    ProductQueryRepositoryDep,
)
from src.modules.shared.depends import ClockDep


def get_category_service(
    command_repository: CategoryCommandRepositoryDep,
    clock: ClockDep,
) -> CategoryService:
    """Создает доменный сервис категорий для FastAPI DI."""
    return CategoryService(
        command_repository=command_repository,
        clock=clock,
    )


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


def get_product_service(
    command_repository: ProductCommandRepositoryDep,
    category_repository: CategoryCommandRepositoryDep,
    clock: ClockDep,
) -> ProductService:
    """Создает доменный сервис товаров для FastAPI DI."""
    return ProductService(
        command_repository=command_repository,
        category_repository=category_repository,
        clock=clock,
    )


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


def get_create_product_use_case(
    service: ProductServiceDep,
) -> CreateProductUseCase:
    """Создает use case создания товара."""
    return CreateProductUseCase(service)


CreateProductUseCaseDep = Annotated[
    CreateProductUseCase,
    Depends(get_create_product_use_case),
]


def get_get_product_use_case(
    query_repository: ProductQueryRepositoryDep,
) -> GetProductUseCase:
    """Создает use case получения товара."""
    return GetProductUseCase(query_repository)


GetProductUseCaseDep = Annotated[
    GetProductUseCase,
    Depends(get_get_product_use_case),
]


def get_list_products_use_case(
    query_repository: ProductQueryRepositoryDep,
) -> ListProductsUseCase:
    """Создает use case списка товаров."""
    return ListProductsUseCase(query_repository)


ListProductsUseCaseDep = Annotated[
    ListProductsUseCase,
    Depends(get_list_products_use_case),
]


def get_update_product_use_case(
    service: ProductServiceDep,
) -> UpdateProductUseCase:
    """Создает use case обновления товара."""
    return UpdateProductUseCase(service)


UpdateProductUseCaseDep = Annotated[
    UpdateProductUseCase,
    Depends(get_update_product_use_case),
]


def get_delete_product_use_case(
    service: ProductServiceDep,
) -> DeleteProductUseCase:
    """Создает use case удаления товара."""
    return DeleteProductUseCase(service)


DeleteProductUseCaseDep = Annotated[
    DeleteProductUseCase,
    Depends(get_delete_product_use_case),
]


def get_describe_product_fields_use_case(
    repository: ProductFieldsDescriptionRepositoryDep,
) -> DescribeProductFieldsUseCase:
    """Создает use case чтения описания модели product."""
    return DescribeProductFieldsUseCase(repository)


DescribeProductFieldsUseCaseDep = Annotated[
    DescribeProductFieldsUseCase,
    Depends(get_describe_product_fields_use_case),
]


def get_create_category_use_case(
    service: CategoryServiceDep,
) -> CreateCategoryUseCase:
    """Создает use case создания категории."""
    return CreateCategoryUseCase(service)


CreateCategoryUseCaseDep = Annotated[
    CreateCategoryUseCase,
    Depends(get_create_category_use_case),
]


def get_get_category_use_case(
    query_repository: CategoryQueryRepositoryDep,
) -> GetCategoryUseCase:
    """Создает use case получения категории."""
    return GetCategoryUseCase(query_repository)


GetCategoryUseCaseDep = Annotated[
    GetCategoryUseCase,
    Depends(get_get_category_use_case),
]


def get_list_categories_use_case(
    query_repository: CategoryQueryRepositoryDep,
) -> ListCategoriesUseCase:
    """Создает use case списка категорий."""
    return ListCategoriesUseCase(query_repository)


ListCategoriesUseCaseDep = Annotated[
    ListCategoriesUseCase,
    Depends(get_list_categories_use_case),
]


def get_update_category_use_case(
    service: CategoryServiceDep,
) -> UpdateCategoryUseCase:
    """Создает use case обновления категории."""
    return UpdateCategoryUseCase(service)


UpdateCategoryUseCaseDep = Annotated[
    UpdateCategoryUseCase,
    Depends(get_update_category_use_case),
]


def get_delete_category_use_case(
    service: CategoryServiceDep,
) -> DeleteCategoryUseCase:
    """Создает use case удаления категории."""
    return DeleteCategoryUseCase(service)


DeleteCategoryUseCaseDep = Annotated[
    DeleteCategoryUseCase,
    Depends(get_delete_category_use_case),
]


def get_describe_category_fields_use_case(
    repository: CategoryFieldsDescriptionRepositoryDep,
) -> DescribeCategoryFieldsUseCase:
    """Создает use case чтения описания модели product_category."""
    return DescribeCategoryFieldsUseCase(repository)


DescribeCategoryFieldsUseCaseDep = Annotated[
    DescribeCategoryFieldsUseCase,
    Depends(get_describe_category_fields_use_case),
]


__all__ = [
    "CategoryServiceDep",
    "CreateCategoryUseCaseDep",
    "CreateProductUseCaseDep",
    "DeleteCategoryUseCaseDep",
    "DeleteProductUseCaseDep",
    "DescribeCategoryFieldsUseCaseDep",
    "DescribeProductFieldsUseCaseDep",
    "GetCategoryUseCaseDep",
    "GetProductUseCaseDep",
    "ListCategoriesUseCaseDep",
    "ListProductsUseCaseDep",
    "ProductServiceDep",
    "UpdateCategoryUseCaseDep",
    "UpdateProductUseCaseDep",
    "get_category_service",
    "get_create_category_use_case",
    "get_create_product_use_case",
    "get_delete_category_use_case",
    "get_delete_product_use_case",
    "get_describe_category_fields_use_case",
    "get_describe_product_fields_use_case",
    "get_get_category_use_case",
    "get_get_product_use_case",
    "get_list_categories_use_case",
    "get_list_products_use_case",
    "get_product_service",
    "get_update_category_use_case",
    "get_update_product_use_case",
]

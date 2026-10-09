from typing import Annotated
from fastapi import Depends
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.rich_text import RichTextSanitizerPort
from src.modules.catalog.application.product_type.schema_service import (
    ProductSchemaService,
)
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.domain.content_block.repository import (
    ContentBlockRepositoryProtocol,
)
from src.modules.catalog.infrastructure.product.persistence.repository import (
    SqlAlchemyProductRepository,
)
from src.modules.catalog.infrastructure.product_type.persistence.repository import (
    SqlAlchemyProductTypeRepository,
)
from src.modules.catalog.infrastructure.content_block.persistence.repository import (
    SqlAlchemyContentBlockRepository,
)
from src.modules.catalog.infrastructure.mutation_lock import PostgresCatalogMutationLock
from src.modules.catalog.infrastructure.locales import ReferenceDataLocales
from src.modules.catalog.infrastructure.rich_text import Nh3RichTextSanitizer
from src.modules.reference_data.presentation.depends import CatalogRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_product_repository(uow: UoWDep) -> ProductRepositoryProtocol:
    """Собирает write repository на общей tenant-сессии."""
    return SqlAlchemyProductRepository(uow.session)


ProductRepositoryDep = Annotated[
    ProductRepositoryProtocol, Depends(get_product_repository)
]


def get_product_type_repository(uow: UoWDep) -> ProductTypeRepositoryProtocol:
    """Собирает write repository типа на той же сессии."""
    return SqlAlchemyProductTypeRepository(uow.session)


ProductTypeRepositoryDep = Annotated[
    ProductTypeRepositoryProtocol, Depends(get_product_type_repository)
]


def get_content_block_repository(uow: UoWDep) -> ContentBlockRepositoryProtocol:
    """Собирает write repository определения блока."""
    return SqlAlchemyContentBlockRepository(uow.session)


ContentBlockRepositoryDep = Annotated[
    ContentBlockRepositoryProtocol, Depends(get_content_block_repository)
]


def get_mutation_lock(uow: UoWDep) -> CatalogMutationLockPort:
    """Подключает transaction lock к общей сессии процесса."""
    return PostgresCatalogMutationLock(uow.session)


MutationLockDep = Annotated[CatalogMutationLockPort, Depends(get_mutation_lock)]


def get_locales(reference: CatalogRepositoryDep) -> LocalePort:
    """Использует публичный Application-контракт reference_data."""
    return ReferenceDataLocales(reference)


LocalesDep = Annotated[LocalePort, Depends(get_locales)]


def get_sanitizer() -> RichTextSanitizerPort:
    """Собирает чистый адаптер HTML-очистки."""
    return Nh3RichTextSanitizer()


SanitizerDep = Annotated[RichTextSanitizerPort, Depends(get_sanitizer)]


def get_schema_service(
    types: ProductTypeRepositoryDep, blocks: ContentBlockRepositoryDep
) -> ProductSchemaService:
    """Координирует контракт снимка на общей сессии."""
    return ProductSchemaService(types, blocks)


SchemaServiceDep = Annotated[ProductSchemaService, Depends(get_schema_service)]

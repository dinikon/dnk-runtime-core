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

from src.modules.catalog.domain.attribute.repository import AttributeRepositoryProtocol
from src.modules.catalog.infrastructure.attribute.persistence.repository import (
    SqlAlchemyAttributeRepository,
)
from src.modules.catalog.application.product.port.attribute_definitions import (
    AttributeDefinitionsPort,
)
from src.modules.catalog.infrastructure.product.attribute_definitions import (
    SqlAlchemyAttributeDefinitions,
)
from src.modules.catalog.application.product.structure_service import (
    ProductStructureService,
)
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_attribute_repository(uow: UoWDep) -> AttributeRepositoryProtocol:
    """Собирает enum write repository на общей tenant-сессии."""
    return SqlAlchemyAttributeRepository(uow.session)


AttributeRepositoryDep = Annotated[
    AttributeRepositoryProtocol, Depends(get_attribute_repository)
]


def get_attribute_definitions(uow: UoWDep) -> AttributeDefinitionsPort:
    """Собирает минимальные снимки на том же UoW, что и Product."""
    return SqlAlchemyAttributeDefinitions(uow.session)


AttributeDefinitionsDep = Annotated[
    AttributeDefinitionsPort, Depends(get_attribute_definitions)
]


def get_structure_service(
    definitions: AttributeDefinitionsDep, uuid: UuidDep
) -> ProductStructureService:
    """Подключает порты генерации ID и снимков к координатору структуры."""
    return ProductStructureService(definitions, uuid)


StructureServiceDep = Annotated[ProductStructureService, Depends(get_structure_service)]

from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol
from src.modules.catalog.infrastructure.category.persistence.repository import (
    SqlAlchemyCategoryRepository,
)


def get_category_repository(uow: UoWDep) -> CategoryRepositoryProtocol:
    """Собирает write repository category на общей tenant-сессии."""
    return SqlAlchemyCategoryRepository(uow.session)


CategoryRepositoryDep = Annotated[
    CategoryRepositoryProtocol, Depends(get_category_repository)
]

from src.modules.catalog.domain.tag.repository import TagRepositoryProtocol
from src.modules.catalog.infrastructure.tag.persistence.repository import (
    SqlAlchemyTagRepository,
)


def get_tag_repository(uow: UoWDep) -> TagRepositoryProtocol:
    """Собирает write repository tag на общей tenant-сессии."""
    return SqlAlchemyTagRepository(uow.session)


TagRepositoryDep = Annotated[TagRepositoryProtocol, Depends(get_tag_repository)]

from src.modules.catalog.application.category.port.tree import CategoryTreePort
from src.modules.catalog.infrastructure.category.tree import SqlAlchemyCategoryTree
from src.modules.catalog.application.product.port.classification_references import (
    ClassificationReferencesPort,
)
from src.modules.catalog.infrastructure.product.classification_references import (
    SqlAlchemyClassificationReferences,
)


def get_category_tree(uow: UoWDep) -> CategoryTreePort:
    """Подключает минимальный снимок дерева к тому же UoW."""
    return SqlAlchemyCategoryTree(uow.session)


CategoryTreeDep = Annotated[CategoryTreePort, Depends(get_category_tree)]


def get_classification_references(uow: UoWDep) -> ClassificationReferencesPort:
    """Подключает ссылки справочников на общей tenant-сессии Product."""
    return SqlAlchemyClassificationReferences(uow.session)


ClassificationReferencesDep = Annotated[
    ClassificationReferencesPort, Depends(get_classification_references)
]

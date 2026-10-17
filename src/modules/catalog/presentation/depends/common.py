from typing import Annotated
from fastapi import Depends
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.rich_text import RichTextSanitizerPort
from src.modules.catalog.infrastructure.mutation_lock import PostgresCatalogMutationLock
from src.modules.catalog.infrastructure.locales import ReferenceDataLocales
from src.modules.catalog.infrastructure.rich_text import Nh3RichTextSanitizer
from src.modules.reference_data.presentation.depends import CatalogRepositoryDep
from src.modules.shared.presentation.persistence.depends import UoWDep


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


from src.modules.catalog.domain.attribute.repository import AttributeRepositoryProtocol
from src.modules.catalog.infrastructure.attribute.persistence.repository import (
    SqlAlchemyAttributeRepository,
)


def get_attribute_repository(uow: UoWDep) -> AttributeRepositoryProtocol:
    """Собирает write repository справочника на общей сессии."""
    return SqlAlchemyAttributeRepository(uow.session)


AttributeRepositoryDep = Annotated[
    AttributeRepositoryProtocol, Depends(get_attribute_repository)
]

from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol
from src.modules.catalog.infrastructure.category.persistence.repository import (
    SqlAlchemyCategoryRepository,
)


def get_category_repository(uow: UoWDep) -> CategoryRepositoryProtocol:
    """Собирает write repository справочника на общей сессии."""
    return SqlAlchemyCategoryRepository(uow.session)


CategoryRepositoryDep = Annotated[
    CategoryRepositoryProtocol, Depends(get_category_repository)
]

from src.modules.catalog.domain.tag.repository import TagRepositoryProtocol
from src.modules.catalog.infrastructure.tag.persistence.repository import (
    SqlAlchemyTagRepository,
)


def get_tag_repository(uow: UoWDep) -> TagRepositoryProtocol:
    """Собирает write repository справочника на общей сессии."""
    return SqlAlchemyTagRepository(uow.session)


TagRepositoryDep = Annotated[TagRepositoryProtocol, Depends(get_tag_repository)]

from src.modules.catalog.application.category.port.tree import CategoryTreePort
from src.modules.catalog.infrastructure.category.tree import SqlAlchemyCategoryTree


def get_category_tree(uow: UoWDep) -> CategoryTreePort:
    """Подключает снимок дерева в общий UoW."""
    return SqlAlchemyCategoryTree(uow.session)


CategoryTreeDep = Annotated[CategoryTreePort, Depends(get_category_tree)]

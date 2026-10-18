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

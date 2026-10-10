from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.files.application.storage_provider.query.list_providers.handler import (
    ListProvidersHandler,
)
from src.modules.files.infrastructure.assembly import build_files_handlers


def get_list_providers_handler(uow: UoWDep) -> ListProvidersHandler:
    """Собирает чтение на общей tenant-сессии request UoW."""
    return build_files_handlers(uow.session).providers


ListProvidersHandlerDep = Annotated[
    ListProvidersHandler, Depends(get_list_providers_handler)
]

from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.files.application.bucket.query.list_buckets.handler import (
    ListBucketsHandler,
)
from src.modules.files.infrastructure.assembly import build_files_handlers


def get_list_buckets_handler(uow: UoWDep) -> ListBucketsHandler:
    """Собирает чтение на общей tenant-сессии request UoW."""
    return build_files_handlers(uow.session).buckets


ListBucketsHandlerDep = Annotated[ListBucketsHandler, Depends(get_list_buckets_handler)]

from typing import Annotated
from src.modules.files.application.stored_file.command.request_trash_empty.handler import (
    RequestTrashEmptyHandler,
)
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.application.stored_file.query.list_files.handler import (
    ListFilesHandler,
)
from src.modules.files.application.stored_file.query.list_trashed_files.handler import (
    ListTrashedFilesHandler,
)
from src.modules.files.application.stored_file.query.get_files_overview.handler import (
    GetFilesOverviewHandler,
)
from src.modules.files.application.stored_file.query.get_file_preview.handler import (
    GetFilePreviewHandler,
)
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.files.application.stored_file.command.upload_file.handler import (
    UploadFileHandler,
)
from src.modules.files.application.stored_file.command.trash_file.handler import (
    TrashFileHandler,
)
from src.modules.files.application.stored_file.command.restore_file.handler import (
    RestoreFileHandler,
)
from src.modules.files.application.stored_file.command.request_file_purge.handler import (
    RequestFilePurgeHandler,
)


def get_list_files_handler(uow: UoWDep) -> ListFilesHandler:
    """Собирает list_files на общей сессии внешнего tenant UoW."""
    return build_files_handlers(uow.session).files


ListFilesHandlerDep = Annotated[ListFilesHandler, Depends(get_list_files_handler)]


def get_list_trashed_files_handler(uow: UoWDep) -> ListTrashedFilesHandler:
    """Собирает list_trashed_files на общей сессии внешнего tenant UoW."""
    return build_files_handlers(uow.session).trash


ListTrashedFilesHandlerDep = Annotated[
    ListTrashedFilesHandler, Depends(get_list_trashed_files_handler)
]


def get_get_files_overview_handler(uow: UoWDep) -> GetFilesOverviewHandler:
    """Собирает get_files_overview на общей сессии внешнего tenant UoW."""
    return build_files_handlers(uow.session).overview


GetFilesOverviewHandlerDep = Annotated[
    GetFilesOverviewHandler, Depends(get_get_files_overview_handler)
]


def get_get_file_preview_handler(uow: UoWDep) -> GetFilePreviewHandler:
    """Собирает предпросмотр на сессии внешнего tenant UoW."""
    return build_files_handlers(uow.session).preview


GetFilePreviewHandlerDep = Annotated[
    GetFilePreviewHandler, Depends(get_get_file_preview_handler)
]


def get_upload_file_handler(
    uow: UoWDep, clock: ClockDep, uuid_generator: UuidDep
) -> UploadFileHandler:
    """Собирает upload_file на общей сессии с доверенными часами и генератором UUID."""
    return build_files_handlers(
        uow.session, clock=clock, uuid_generator=uuid_generator
    ).upload


UploadFileHandlerDep = Annotated[UploadFileHandler, Depends(get_upload_file_handler)]


def get_trash_file_handler(
    uow: UoWDep, clock: ClockDep, uuid_generator: UuidDep
) -> TrashFileHandler:
    """Собирает trash_file на общей сессии с доверенными часами и генератором UUID."""
    return build_files_handlers(
        uow.session, clock=clock, uuid_generator=uuid_generator
    ).trash_file


TrashFileHandlerDep = Annotated[TrashFileHandler, Depends(get_trash_file_handler)]


def get_restore_file_handler(
    uow: UoWDep, clock: ClockDep, uuid_generator: UuidDep
) -> RestoreFileHandler:
    """Собирает restore_file на общей сессии с доверенными часами и генератором UUID."""
    return build_files_handlers(
        uow.session, clock=clock, uuid_generator=uuid_generator
    ).restore


RestoreFileHandlerDep = Annotated[RestoreFileHandler, Depends(get_restore_file_handler)]


def get_request_file_purge_handler(
    uow: UoWDep, clock: ClockDep, uuid_generator: UuidDep
) -> RequestFilePurgeHandler:
    """Собирает request_file_purge на общей сессии с доверенными часами и генератором UUID."""
    return build_files_handlers(
        uow.session, clock=clock, uuid_generator=uuid_generator
    ).request_purge


RequestFilePurgeHandlerDep = Annotated[
    RequestFilePurgeHandler, Depends(get_request_file_purge_handler)
]


def get_request_trash_empty_handler(
    uow: UoWDep, clock: ClockDep, uuid_generator: UuidDep
) -> RequestTrashEmptyHandler:
    """Собирает запрос очистки на общей сессии function-scoped tenant UoW."""
    return build_files_handlers(
        uow.session, clock=clock, uuid_generator=uuid_generator
    ).request_trash_empty


RequestTrashEmptyHandlerDep = Annotated[
    RequestTrashEmptyHandler, Depends(get_request_trash_empty_handler)
]

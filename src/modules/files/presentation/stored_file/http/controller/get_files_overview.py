from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.files.presentation.depends.admin import FilesAdminContextDep
from src.modules.files.presentation.stored_file.depends import (
    GetFilesOverviewHandlerDep,
)
from src.modules.files.presentation.stored_file.http.response.get_files_overview import (
    GetFilesOverviewResponse,
)
from src.modules.files.application.stored_file.query.get_files_overview.query import (
    GetFilesOverviewQuery,
)
from src.modules.files.application.stored_file.error import InvalidFileQueryError
from src.modules.files.domain.error import (
    StorageNotFoundError,
    InvalidStorageStateError,
)


async def get_files_overview(
    context: FilesAdminContextDep,
    handler: GetFilesOverviewHandlerDep,
    bucket_id: Annotated[list[UUID] | None, Query(max_length=50)] = None,
) -> GetFilesOverviewResponse:
    """Читает общую сводку выбранных дисков без поиска и фильтра категории."""
    assert context.principal is not None and context.principal.tenant_id is not None
    query = GetFilesOverviewQuery(
        tenant_id=UUID(context.principal.tenant_id), bucket_ids=tuple(bucket_id or ())
    )
    try:
        result = await handler.execute(query)
    except StorageNotFoundError as error:
        raise HTTPException(404, "Selected storage was not found.") from error
    except InvalidStorageStateError as error:
        raise HTTPException(409, "Selected storage is not ready.") from error
    except InvalidFileQueryError as error:
        raise HTTPException(422, "Invalid bucket filters.") from error
    return GetFilesOverviewResponse.from_dto(result)

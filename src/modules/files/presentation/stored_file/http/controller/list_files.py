from typing import Annotated
from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.files.presentation.depends.admin import FilesAdminContextDep
from src.modules.files.presentation.stored_file.depends import ListFilesHandlerDep
from src.modules.files.presentation.stored_file.http.response.list_files import (
    ListFilesResponse,
)
from src.modules.files.application.stored_file.query.list_files.query import (
    ListFilesQuery,
)
from src.modules.files.application.stored_file.file_category import FileCategory
from src.modules.files.application.stored_file.error import InvalidFileQueryError
from src.modules.files.domain.error import (
    StorageNotFoundError,
    InvalidStorageStateError,
)


async def list_files(
    context: FilesAdminContextDep,
    handler: ListFilesHandlerDep,
    search: Annotated[
        str, Query(description="Подстрока имени; после trim до 255 символов.")
    ] = "",
    bucket_id: Annotated[list[UUID] | None, Query(max_length=50)] = None,
    category: FileCategory | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int, Query(json_schema_extra={"enum": [10, 20, 50, 100]})
    ] = 20,
) -> ListFilesResponse:
    """Преобразует HTTP-фильтры и trusted tenant в запрос списка файлов."""
    assert context.principal is not None and context.principal.tenant_id is not None
    query = ListFilesQuery(
        tenant_id=UUID(context.principal.tenant_id),
        search=search,
        bucket_ids=tuple(bucket_id or ()),
        category=category,
        page=page,
        page_size=page_size,
    )
    try:
        result = await handler.execute(query)
    except StorageNotFoundError as error:
        raise HTTPException(404, "Selected storage was not found.") from error
    except InvalidStorageStateError as error:
        raise HTTPException(409, "Selected storage is not ready.") from error
    except InvalidFileQueryError as error:
        raise HTTPException(422, "Invalid file filters or pagination.") from error
    return ListFilesResponse.from_dto(result)

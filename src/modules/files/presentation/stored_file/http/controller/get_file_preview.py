from uuid import UUID

from fastapi import HTTPException

from src.modules.files.application.port.storage import (
    StorageConfigurationError,
    StorageOwnershipError,
    StorageUnavailableError,
)
from src.modules.files.application.stored_file.error import UnsupportedFilePreviewError
from src.modules.files.application.stored_file.query.get_file_preview.query import (
    GetFilePreviewQuery,
)
from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.presentation.depends.admin import FilesPreviewContextDep
from src.modules.files.presentation.stored_file.depends import GetFilePreviewHandlerDep
from src.modules.files.presentation.stored_file.http.response.get_file_preview import (
    GetFilePreviewResponse,
)
from src.modules.files.presentation.stored_file.stream_depends import (
    PreviewStreamsDep,
    close_preview_stream,
)


async def get_file_preview(
    file_id: UUID,
    context: FilesPreviewContextDep,
    handler: GetFilePreviewHandlerDep,
    streams: PreviewStreamsDep,
) -> GetFilePreviewResponse:
    """Возвращает поток готового файла текущего tenant только авторизованному admin."""
    assert context.principal is not None and context.principal.tenant_id is not None
    try:
        result = await handler.execute(
            GetFilePreviewQuery(UUID(context.principal.tenant_id), file_id)
        )
    except FileNotFoundError as error:
        raise HTTPException(404, "File is not available.") from error
    except UnsupportedFilePreviewError as error:
        raise HTTPException(415, "File format does not support preview.") from error
    except StorageOwnershipError as error:
        raise HTTPException(409, "File storage ownership is not confirmed.") from error
    except (StorageUnavailableError, StorageConfigurationError) as error:
        raise HTTPException(503, "File storage is unavailable.") from error
    try:
        response = GetFilePreviewResponse.from_dto(result)
    except BaseException:
        await close_preview_stream(result.stream)
        raise
    # Request-scoped cleanup сработает и при ошибке commit до отправки ответа.
    streams.push_async_callback(response.aclose)
    return response

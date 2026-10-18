from fastapi import HTTPException
from src.modules.files.domain.error import (
    FileNotFoundError,
    StorageNotFoundError,
    InvalidStorageStateError,
    InvalidFileError,
)
from src.modules.files.domain.stored_file.error import FileStateConflictError
from src.modules.files.application.port.storage import (
    StorageOwnershipError,
    StorageConfigurationError,
    StorageUnavailableError,
)
from uuid import UUID
from src.modules.files.presentation.depends.admin import FilesUploadContextDep
from src.modules.files.presentation.stored_file.depends import UploadFileHandlerDep
from src.modules.files.presentation.stored_file.multipart import UploadFileRequestDep
from src.modules.files.presentation.stored_file.http.response.upload_file import (
    UploadFileResponse,
)
from src.modules.files.application.stored_file.command.upload_file.command import (
    UploadFileCommand,
)


async def upload_file(
    context: FilesUploadContextDep,
    payload: UploadFileRequestDep,
    handler: UploadFileHandlerDep,
) -> UploadFileResponse:
    """Передаёт spool и фактический размер существующему upload use case, закрывая источник."""
    assert context.principal is not None and context.principal.tenant_id is not None
    source = payload.file
    try:
        if source.size is None:
            raise HTTPException(422, "Actual file size is required.")
        command = UploadFileCommand(
            tenant_id=UUID(context.principal.tenant_id),
            source=source.file,
            size_bytes=source.size,
            name=source.filename or "",
            content_type=source.content_type or "application/octet-stream",
            bucket_id=payload.bucket_id,
        )
        result = await handler.execute(command)
        return UploadFileResponse.from_dto(result)
    except (FileNotFoundError, StorageNotFoundError) as error:
        raise HTTPException(404, "File or storage was not found.") from error
    except (
        FileStateConflictError,
        InvalidStorageStateError,
        StorageOwnershipError,
    ) as error:
        raise HTTPException(
            409, "File or storage state does not allow this operation."
        ) from error
    except InvalidFileError as error:
        raise HTTPException(422, "Invalid file metadata or content.") from error
    except (StorageUnavailableError, StorageConfigurationError) as error:
        raise HTTPException(503, "File storage is unavailable.") from error
    finally:
        await source.close()

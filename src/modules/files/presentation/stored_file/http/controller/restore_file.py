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
from src.modules.files.presentation.depends.admin import FilesRestoreContextDep
from src.modules.files.presentation.stored_file.depends import RestoreFileHandlerDep
from src.modules.files.application.stored_file.command.restore_file.command import (
    RestoreFileCommand,
)
from src.modules.files.presentation.stored_file.http.response.restore_file import (
    RestoreFileResponse,
)


async def restore_file(
    file_id: UUID, context: FilesRestoreContextDep, handler: RestoreFileHandlerDep
) -> RestoreFileResponse:
    """Преобразует path и trusted principal в команду restore_file без тела запроса."""
    assert context.principal is not None and context.principal.tenant_id is not None
    command = RestoreFileCommand(
        tenant_id=UUID(context.principal.tenant_id),
        file_id=file_id,
        actor_id=UUID(context.principal.user_id),
    )
    try:
        result = await handler.execute(command)
        return RestoreFileResponse.from_dto(result)
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

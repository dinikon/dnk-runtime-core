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
from src.modules.files.presentation.depends.admin import FilesPurgeContextDep
from src.modules.files.presentation.stored_file.depends import (
    RequestFilePurgeHandlerDep,
)
from src.modules.files.application.stored_file.command.request_file_purge.command import (
    RequestFilePurgeCommand,
)
from fastapi import Response


async def request_file_purge(
    file_id: UUID, context: FilesPurgeContextDep, handler: RequestFilePurgeHandlerDep
) -> Response:
    """Преобразует path и trusted principal в команду request_file_purge без тела запроса."""
    assert context.principal is not None and context.principal.tenant_id is not None
    command = RequestFilePurgeCommand(
        tenant_id=UUID(context.principal.tenant_id),
        file_id=file_id,
        actor_id=UUID(context.principal.user_id),
    )
    try:
        await handler.execute(command)
        return Response(status_code=202)
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

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.application.content_block.command.create_content_block.command import (
    CreateContentBlockCommand,
)
from src.modules.catalog.domain.content_block.error import (
    ContentBlockNotFoundError,
    ContentBlockConflictError,
    InvalidContentBlockError,
)
from src.modules.catalog.presentation.content_block.depends import (
    CreateContentBlockHandlerDep,
)
from src.modules.catalog.presentation.content_block.http.request.create_block import (
    CreateBlockRequest,
)
from src.modules.catalog.presentation.content_block.http.response.create_block import (
    CreateBlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def create_block(
    payload: CreateBlockRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateContentBlockHandlerDep,
) -> CreateBlockResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        item = await handler.execute(
            CreateContentBlockCommand(payload.code, payload.type, payload.translations)
        )
    except ContentBlockNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ContentBlockConflictError, IntegrityError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (InvalidContentBlockError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateBlockResponse.from_dto(item)

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.application.content_block.command.put_content_block.command import (
    PutContentBlockCommand,
)
from src.modules.catalog.domain.content_block.error import (
    ContentBlockNotFoundError,
    ContentBlockConflictError,
    InvalidContentBlockError,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.presentation.content_block.depends import (
    PutContentBlockHandlerDep,
)
from src.modules.catalog.presentation.content_block.http.request.put_block import (
    PutBlockRequest,
)
from src.modules.catalog.presentation.content_block.http.response.put_block import (
    PutBlockResponse,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def put_block(
    block_id: UUID,
    payload: PutBlockRequest,
    context: AuthenticatedRequestContextDep,
    handler: PutContentBlockHandlerDep,
) -> PutBlockResponse:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        item = await handler.execute(
            PutContentBlockCommand(
                ContentBlockIdVO.from_value(block_id),
                payload.type,
                payload.translations,
            )
        )
    except ContentBlockNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ContentBlockConflictError, IntegrityError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (InvalidContentBlockError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return PutBlockResponse.from_dto(item)

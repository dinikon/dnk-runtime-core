from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.application.content_block.command.delete_content_block.command import (
    DeleteContentBlockCommand,
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
    DeleteContentBlockHandlerDep,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def delete_block(
    block_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: DeleteContentBlockHandlerDep,
) -> None:
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        await handler.execute(
            DeleteContentBlockCommand(ContentBlockIdVO.from_value(block_id))
        )
    except ContentBlockNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ContentBlockConflictError, IntegrityError) as exc:
        raise HTTPException(409, str(exc)) from exc

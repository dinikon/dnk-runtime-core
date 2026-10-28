from uuid import UUID
from fastapi import Query, Response
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.http.access import channel_access
from src.modules.channels.presentation.catalog_binding.depends import (
    DeleteCatalogBindingHandlerDep,
)
from src.modules.channels.application.catalog_binding.command.delete_catalog_binding.command import (
    DeleteCatalogBindingCommand,
)


async def delete_catalog_binding(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: DeleteCatalogBindingHandlerDep,
    channel_id: UUID,
    group_id: UUID,
    expected_revision: int = Query(ge=1),
) -> Response:
    """Авторизует и явно преобразует сценарий delete_catalog_binding."""
    tenant_id, actor_id = await channel_access(
        context, authorization, "manage", channel_id
    )
    result = await handler.execute(
        DeleteCatalogBindingCommand(
            tenant_id=tenant_id,
            channel_id=channel_id,
            group_id=group_id,
            expected_revision=expected_revision,
        )
    )
    return Response(status_code=204)

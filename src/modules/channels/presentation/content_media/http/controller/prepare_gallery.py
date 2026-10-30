from uuid import UUID
from src.modules.channels.application.content_media.command.prepare_gallery.command import (
    PrepareGalleryCommand,
)
from src.modules.channels.presentation.content_media.depends import (
    PrepareGalleryHandlerDep,
)
from src.modules.channels.presentation.content_media.http.request.prepare_gallery import (
    PrepareGalleryRequest,
)
from src.modules.channels.presentation.content_media.http.response.prepare_gallery import (
    PrepareGalleryResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def prepare_gallery(
    channel_id: UUID,
    group_id: UUID,
    payload: PrepareGalleryRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: PrepareGalleryHandlerDep,
) -> PrepareGalleryResponse:
    """Выдаёт URL только после channels.manage, Files ACL и проверки сохранённого контекста."""
    tenant_id, _ = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        PrepareGalleryCommand(
            tenant_id,
            channel_id,
            group_id,
            payload.expected_revision,
            payload.expected_binding_revision,
            payload.expected_config_revision,
        )
    )
    return PrepareGalleryResponse.from_dto(result)

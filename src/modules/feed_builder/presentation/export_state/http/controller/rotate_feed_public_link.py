from uuid import UUID

from fastapi import Request

from src.modules.feed_builder.application.export_state.command.rotate_feed_public_link.command import (
    RotateFeedPublicLinkCommand,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.presentation.export_state.depends import (
    RotateFeedPublicLinkHandlerDep,
)
from src.modules.feed_builder.presentation.export_state.http.errors import (
    export_http_error,
)
from src.modules.feed_builder.presentation.export_state.http.request.rotate_feed_public_link import (
    RotateFeedPublicLinkRequest,
)
from src.modules.feed_builder.presentation.export_state.http.response.rotate_feed_public_link import (
    RotateFeedPublicLinkResponse,
)
from src.modules.feed_builder.presentation.export_state.http.urls import public_feed_url
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def rotate_feed_public_link(
    feed_id: UUID,
    payload: RotateFeedPublicLinkRequest,
    request: Request,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RotateFeedPublicLinkHandlerDep,
) -> RotateFeedPublicLinkResponse:
    """Меняет публичную ссылку по праву редактирования Feed."""
    for action in ("feed_builder.feed.read", "feed_builder.feed.update"):
        await require_feed_access(
            context, authorization, action=action, feed_id=feed_id
        )
    try:
        result = await handler.execute(
            RotateFeedPublicLinkCommand(feed_id, payload.expected_version)
        )
    except FeedBuilderDomainError as exc:
        raise export_http_error(exc) from exc
    return RotateFeedPublicLinkResponse(
        url=public_feed_url(request, result.public_link_id, result.format.value),
        feed_version=result.feed_version,
    )

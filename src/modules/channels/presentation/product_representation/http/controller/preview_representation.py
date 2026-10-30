from uuid import UUID

from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.product_representation.query.preview_representation.query import (
    PreviewRepresentationQuery,
)
from src.modules.channels.domain.channel.error import ChannelError
from src.modules.channels.presentation.http.access import (
    channel_access,
    channel_http_error,
)
from src.modules.channels.presentation.product_representation.depends import (
    PreviewRepresentationHandlerDep,
)
from src.modules.channels.presentation.product_representation.http.request.preview_representation import (
    PreviewRepresentationRequest,
)
from src.modules.channels.presentation.product_representation.http.response.preview_representation import (
    PreviewRepresentationResponse,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def preview_representation(
    channel_id: UUID,
    group_id: UUID,
    payload: PreviewRepresentationRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: PreviewRepresentationHandlerDep,
) -> PreviewRepresentationResponse:
    """Авторизует чтение группы и возвращает вычисленное представление публикаций."""
    await channel_access(context, authorization, "read", channel_id)
    try:
        result = await handler.execute(
            PreviewRepresentationQuery(
                channel_id=channel_id,
                group_id=group_id,
                locales=payload.locales,
                overrides=(
                    payload.overrides.to_value()
                    if payload.overrides is not None
                    else None
                ),
                expected_revision=payload.expected_revision,
                expected_binding_revision=payload.expected_binding_revision,
                expected_config_revision=payload.expected_config_revision,
            )
        )
    except (ChannelError, ChannelInputError) as error:
        raise channel_http_error(error) from None
    return PreviewRepresentationResponse.from_dto(result)

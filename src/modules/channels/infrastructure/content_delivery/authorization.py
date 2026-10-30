from uuid import UUID
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)


class ContentDeliveryAuthorization:
    """Проверяет реального инициатора через публичный контракт Identity."""

    def __init__(
        self, *, tenant_id: UUID, authorization: AuthorizationServiceProtocol
    ) -> None:
        """Принимает одну политику для HTTP и фонового исполнителя."""
        self._tenant_id, self._authorization = tenant_id, authorization

    async def require(
        self, *, actor_id: UUID, channel_id: UUID, file_ids: tuple[UUID, ...]
    ) -> None:
        """Проверяет канал и каждый выбранный файл без подмены principal."""
        if not await self._authorization.can(
            user_id=actor_id,
            tenant_id=self._tenant_id,
            action="channels.manage",
            resource_type="channel",
            resource_id=channel_id,
        ):
            raise ContentDeliveryError("content_access_denied")
        for identifier in sorted(set(file_ids)):
            if not await self._authorization.can(
                user_id=actor_id,
                tenant_id=self._tenant_id,
                action="files.read",
                resource_type="stored_file",
                resource_id=identifier,
            ):
                raise ContentDeliveryError("content_file_forbidden")

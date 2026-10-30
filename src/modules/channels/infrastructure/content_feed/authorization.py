from uuid import UUID
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)


class FeedAuthorization:
    """Проверяет актуальные права владельца разрешения через публичный Identity port."""

    def __init__(
        self, *, tenant_id: UUID, authorization: AuthorizationServiceProtocol
    ) -> None:
        """Использует tenant из доверенного домена."""
        self._tenant_id, self._authorization = tenant_id, authorization

    async def require(
        self, *, actor_id: UUID, channel_id: UUID, file_ids: tuple[UUID, ...]
    ) -> None:
        """Отзыв роли или Files ACL блокирует следующую публичную выдачу."""
        if not await self._authorization.can(
            user_id=actor_id,
            tenant_id=self._tenant_id,
            action="channels.manage",
            resource_type="channel",
            resource_id=channel_id,
        ):
            raise FeedBuildError("feed_access_denied")
        for identifier in sorted(set(file_ids)):
            if not await self._authorization.can(
                user_id=actor_id,
                tenant_id=self._tenant_id,
                action="files.read",
                resource_type="stored_file",
                resource_id=identifier,
            ):
                raise FeedBuildError("feed_file_forbidden")

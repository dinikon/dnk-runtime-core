from uuid import UUID

from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)


class MediaFilesAuthorization:
    """Проверяет существующее право Files для каждого выбранного ресурса."""

    def __init__(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        authorization: AuthorizationServiceProtocol,
    ) -> None:
        """Захватывает доверенные ID из authenticated request context."""
        self._tenant_id, self._actor_id, self._authorization = (
            tenant_id,
            actor_id,
            authorization,
        )

    async def require_files(self, file_ids: tuple[UUID, ...]) -> None:
        """Не расширяет channels.manage до чтения произвольного Files-ресурса."""
        for identifier in sorted(set(file_ids)):
            if not await self._authorization.can(
                user_id=self._actor_id,
                tenant_id=self._tenant_id,
                action="files.read",
                resource_type="stored_file",
                resource_id=identifier,
            ):
                raise ContentMediaError("media_file_forbidden")

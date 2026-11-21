from src.modules.identity.application.user.query.get_current_user.query import (
    GetCurrentUserQuery,
)
from src.modules.identity.application.user.query.get_current_user.dto import (
    GetCurrentUserResultDTO,
)
from src.modules.identity.application.user.port.query_repository import (
    UserProfileQueryRepositoryProtocol,
)
from src.modules.identity.domain.auth.error import InvalidSessionError


class GetCurrentUserHandler:
    """Возвращает проекцию профиля с явно выбранной валютой отображения."""

    def __init__(
        self,
        repository: UserProfileQueryRepositoryProtocol,
    ) -> None:
        """Получает порт чтения профиля на общем внешнем UoW."""
        self._repository = repository

    async def execute(self, query: GetCurrentUserQuery) -> GetCurrentUserResultDTO:
        """Читает профиль по доверенному контексту, не загружая доменный агрегат."""
        result = await self._repository.get_current_user(
            query.user_id, tenant_id=query.tenant_id
        )
        if result is None:
            raise InvalidSessionError()
        return GetCurrentUserResultDTO(
            id=result.id,
            status=result.status,
            role=result.role,
            last_name=result.last_name,
            first_name=result.first_name,
            middle_name=result.middle_name,
            avatar=result.avatar,
            interface_language=result.interface_language,
            interface_theme=result.interface_theme,
            timezone=result.timezone,
            display_currency=result.display_currency,
            emails=result.emails,
        )

from typing import Protocol
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.identity.application.user.query.get_current_user.record_dto import (
    GetCurrentUserRecordDTO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class UserProfileQueryRepositoryProtocol(Protocol):
    """Читает проекцию конкретного профиля без восстановления агрегата."""

    async def get_current_user(
        self, user_id: UserIdVO, *, tenant_id: EntityIdVO
    ) -> GetCurrentUserRecordDTO | None:
        """Возвращает профиль пользователя в привязанной схеме либо None."""
        ...

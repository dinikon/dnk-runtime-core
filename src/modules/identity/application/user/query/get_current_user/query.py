from __future__ import annotations
from dataclasses import dataclass
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetCurrentUserQuery:
    """DTO команды получения текущего пользователя по session."""

    tenant_id: EntityIdVO
    user_id: UserIdVO

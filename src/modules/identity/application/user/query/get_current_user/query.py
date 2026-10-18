from __future__ import annotations
from dataclasses import dataclass
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetCurrentUserQuery:
    """Запрашивает профиль по доверенным User ID и Tenant ID."""

    tenant_id: EntityIdVO
    user_id: UserIdVO

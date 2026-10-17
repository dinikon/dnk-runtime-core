from __future__ import annotations
from dataclasses import dataclass
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class UpdateCurrentUserProfileCommand:
    """DTO команды обновления профиля текущего пользователя."""

    tenant_id: EntityIdVO
    user_id: UserIdVO
    last_name: str
    first_name: str
    middle_name: str | None
    interface_language: str
    interface_theme: str
    timezone: str

    display_currency: str | None = None
    display_currency_provided: bool = False

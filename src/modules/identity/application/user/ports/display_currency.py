from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.identity.domain.user import User
from src.modules.identity.domain.user.value_object import UserIdVO


class DisplayCurrencyValidator(Protocol):
    async def validate(
        self, *, tenant_id: EntityIdVO, currency: CurrencyCodeVO
    ) -> None: ...


class DisplayCurrencyPreferenceRepository(Protocol):
    async def get_by_id(
        self, user_id: UserIdVO, *, tenant_id: EntityIdVO
    ) -> User | None: ...
    async def save_display_currency(
        self, user: User, *, tenant_id: EntityIdVO
    ) -> None: ...
    async def get_display_currency(
        self, *, tenant_id: EntityIdVO, user_id: UserIdVO
    ) -> CurrencyCodeVO | None: ...


__all__ = ["DisplayCurrencyValidator", "DisplayCurrencyPreferenceRepository"]

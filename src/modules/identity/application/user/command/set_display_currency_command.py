from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.identity.domain.user.value_object import UserIdVO


@dataclass(frozen=True, slots=True)
class SetDisplayCurrencyCommand:
    tenant_id: EntityIdVO
    user_id: UserIdVO
    currency: CurrencyCodeVO | None


__all__ = ["SetDisplayCurrencyCommand"]

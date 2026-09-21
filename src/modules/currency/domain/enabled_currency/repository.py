from datetime import datetime
from typing import Protocol
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class EnabledCurrencyRepository(Protocol):
    """Allowed currency storage, scoped explicitly to an organization."""

    async def enabled(self, *, tenant_id: EntityIdVO) -> set[CurrencyCodeVO]: ...

    async def set_enabled(
        self,
        *,
        tenant_id: EntityIdVO,
        code: CurrencyCodeVO,
        enabled: bool,
        now: datetime,
    ) -> None: ...


__all__ = ["EnabledCurrencyRepository"]

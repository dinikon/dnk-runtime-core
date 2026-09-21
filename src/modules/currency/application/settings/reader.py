from typing import Protocol
from src.modules.currency.application.policy.dto.currency_policy_dto import (
    CurrencyPolicyDTO,
)
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CurrencySettingsReader(Protocol):
    """Public read contract for one operation’s immutable organization settings."""

    async def get(self, *, tenant_id: EntityIdVO) -> CurrencyPolicyDTO: ...


class OperationCurrencySettings:
    """Freeze policy reads, including absence, for one publication UnitOfWork."""

    def __init__(self, policies: CurrencyPolicyRepository):
        self.policies = policies
        self._values: dict[EntityIdVO, CurrencyPolicyDTO | None] = {}

    async def get(self, *, tenant_id: EntityIdVO) -> CurrencyPolicyDTO:
        if tenant_id not in self._values:
            try:
                self._values[tenant_id] = CurrencyPolicyDTO.from_entity(
                    await self.policies.get(tenant_id=tenant_id)
                )
            except CurrencyPolicyNotConfigured:
                self._values[tenant_id] = None
        value = self._values[tenant_id]
        if value is None:
            raise CurrencyPolicyNotConfigured(
                "Configure the organization's currency policy first."
            )
        return value


__all__ = ["CurrencySettingsReader", "OperationCurrencySettings"]

from src.modules.currency.application.settings.query.validate_display_currency_query import (
    ValidateDisplayCurrencyQuery,
)
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.directory.repository import CurrencyDirectory
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository


class ValidateDisplayCurrencyUseCase:
    """Validate a new display preference against explicit tenant settings."""

    def __init__(
        self,
        directory: CurrencyDirectory,
        policies: CurrencyPolicyRepository,
        enabled_currencies: EnabledCurrencyRepository,
    ):
        self.directory, self.policies = directory, policies
        self.enabled_currencies = enabled_currencies

    async def __call__(self, query: ValidateDisplayCurrencyQuery) -> None:
        await self.policies.lock(tenant_id=query.tenant_id)
        await self.policies.get(tenant_id=query.tenant_id)
        info = await self.directory.get(query.currency)
        if not info.is_active:
            raise CurrencyNotFound(f"Currency {query.currency} is not active.")
        if query.currency not in await self.enabled_currencies.enabled(
            tenant_id=query.tenant_id
        ):
            raise CurrencyDisabled(f"Currency {query.currency} is not enabled.")


__all__ = ["ValidateDisplayCurrencyUseCase"]

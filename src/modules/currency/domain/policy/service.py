from collections.abc import Iterable
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.directory.repository import CurrencyDirectory
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


class CurrencyPolicyRules:
    """Validate currencies referenced by tenant configuration."""

    def __init__(self, directory: CurrencyDirectory):
        self.directory = directory

    async def validate_codes(self, codes: Iterable[CurrencyCodeVO]) -> None:
        for code in set(codes):
            info = await self.directory.get(code)
            if not info.is_active:
                raise CurrencyNotFound(f"Currency {code} is not active.")

    @staticmethod
    def required_codes(policy: CurrencyPolicy) -> set[CurrencyCodeVO]:
        return (
            {policy.default_transaction_currency}
            | ({policy.bridge_currency} if policy.allow_cross_rate else set())
            | (
                {policy.default_display_currency}
                if policy.default_display_currency
                else set()
            )
        )


__all__ = ["CurrencyPolicyRules"]

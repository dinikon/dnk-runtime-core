from __future__ import annotations
from datetime import date
from decimal import Decimal, Context
from decimal import localcontext
from src.modules.currency.domain.directory.entity import CurrencyInfo
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.directory.repository import CurrencyDirectory
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.currency.domain.exchange_rate.error import CrossRateUnavailable
from src.modules.currency.domain.exchange_rate.error import ExchangeRateNotFound
from src.modules.currency.domain.exchange_rate.repository import RateRepository
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.exchange_rate.value_object.rate_derivation import (
    RateDerivation,
)
from src.modules.currency.domain.exchange_rate.value_object.rate_quote import RateQuote
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ExchangeRateResolver:
    """Resolves locally stored quotes; never owns a provider HTTP adapter."""

    def __init__(
        self,
        rates: RateRepository,
        policies: CurrencyPolicyRepository,
        directory: CurrencyDirectory,
        enabled_currencies: EnabledCurrencyRepository,
    ):
        self.rates, self.policies, self.directory = rates, policies, directory
        self.enabled_currencies = enabled_currencies

    async def resolve(
        self,
        *,
        tenant_id: EntityIdVO,
        pair: CurrencyPair,
        requested_date: date,
        policy: CurrencyPolicy | None = None,
        enabled: set[CurrencyCodeVO] | None = None,
        directory: dict[CurrencyCodeVO, CurrencyInfo] | None = None,
    ) -> RateQuote:
        policy = policy or await self.policies.get(tenant_id=tenant_id)
        if enabled is None:
            enabled = await self.enabled_currencies.enabled(tenant_id=tenant_id)
        for code in {pair.source, pair.target}:
            info = (
                directory.get(code)
                if directory is not None
                else await self.directory.get(code)
            )
            if info is None or not info.is_active:
                raise CurrencyNotFound(f"Currency {code} is not active.")
            if code not in enabled:
                raise CurrencyDisabled(f"Currency {code} is not enabled.")
        if pair.source == pair.target:
            return RateQuote(
                pair,
                Decimal(1),
                requested_date,
                requested_date,
                ProviderCode("INTERNAL"),
                RateDerivation.IDENTITY,
            )
        args = dict(
            tenant_id=tenant_id,
            provider=policy.provider_code,
            requested_date=requested_date,
            policy=policy.rate_date_policy,
        )
        direct = await self.rates.find(pair=pair, **args)
        if direct is not None:
            return RateQuote(
                pair,
                direct.rate,
                requested_date,
                direct.effective_date,
                policy.provider_code,
                RateDerivation.DIRECT,
                (direct.id,),
            )
        inverse = await self.rates.find(pair=pair.inverse(), **args)
        if inverse is not None:
            with localcontext(
                Context(prec=38, rounding=policy.rounding_mode.value)
            ) as context:
                context.prec = 38
                context.rounding = policy.rounding_mode.value
                return RateQuote(
                    pair,
                    Decimal(1) / inverse.rate,
                    requested_date,
                    inverse.effective_date,
                    policy.provider_code,
                    RateDerivation.INVERSE,
                    (inverse.id,),
                )
        if policy.allow_cross_rate and policy.bridge_currency not in (
            pair.source,
            pair.target,
        ):
            legs = await self.rates.find_cross(
                pair=pair, bridge=policy.bridge_currency, **args
            )
            if legs is not None:
                first, second = legs
                if (
                    first.effective_date != second.effective_date
                    or first.provider_code != policy.provider_code
                    or second.provider_code != policy.provider_code
                ):
                    raise CrossRateUnavailable(
                        "Cross-rate legs must use the same effective date."
                    )
                with localcontext(
                    Context(prec=38, rounding=policy.rounding_mode.value)
                ) as context:
                    context.prec = max(
                        38,
                        len(first.rate.as_tuple().digits)
                        + len(second.rate.as_tuple().digits),
                    )
                    numerator = (
                        first.rate if first.pair.source == pair.source else Decimal(1)
                    ) * (
                        second.rate
                        if second.pair.source == policy.bridge_currency
                        else Decimal(1)
                    )
                    denominator = (
                        Decimal(1) if first.pair.source == pair.source else first.rate
                    ) * (
                        Decimal(1)
                        if second.pair.source == policy.bridge_currency
                        else second.rate
                    )
                    context.prec = 38
                    context.rounding = policy.rounding_mode.value
                    return RateQuote(
                        pair,
                        numerator / denominator,
                        requested_date,
                        first.effective_date,
                        policy.provider_code,
                        RateDerivation.CROSS,
                        (first.id, second.id),
                        policy.bridge_currency,
                    )
            raise CrossRateUnavailable(
                f"No common-date cross rate for {pair.source}/{pair.target} on {requested_date}."
            )
        raise ExchangeRateNotFound(
            f"No {policy.provider_code} rate for {pair.source}/{pair.target} on {requested_date}."
        )


__all__ = ["ExchangeRateResolver"]

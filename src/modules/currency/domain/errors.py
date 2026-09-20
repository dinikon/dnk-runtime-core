from src.modules.shared.domain.domain_error import DomainError


class CurrencyError(DomainError):
    code = "currency_error"


class CurrencyNotFound(CurrencyError):
    code = "currency_not_found"


class CurrencyDisabled(CurrencyError):
    code = "currency_disabled"


class CurrencyPolicyNotConfigured(CurrencyError):
    code = "policy_not_configured"


class CurrencyConflict(CurrencyError):
    code = "currency_conflict"


class InvalidExchangeRate(CurrencyError):
    code = "invalid_exchange_rate"


class ExchangeRateNotFound(CurrencyError):
    code = "exchange_rate_not_found"


class CrossRateUnavailable(ExchangeRateNotFound):
    code = "cross_rate_unavailable"


class FunctionalCurrencyNotConfigured(CurrencyError):
    code = "functional_currency_not_configured"


class FunctionalCurrencyPeriodOverlap(CurrencyConflict):
    code = "functional_currency_period_overlap"


class FunctionalCurrencyChangeNotAllowed(CurrencyConflict):
    code = "functional_currency_change_not_allowed"


class ProviderUnavailable(CurrencyError):
    code = "provider_unavailable"


class ProviderRateInvalid(CurrencyError):
    code = "provider_rate_invalid"


class CurrencyPrecisionUndefined(CurrencyError):
    code = "currency_precision_undefined"

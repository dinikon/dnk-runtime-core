from src.modules.shared.domain.domain_error import DomainError


class InvalidCurrencyCodeError(DomainError):
    """A currency code must contain exactly three ASCII letters."""

    code = "invalid_currency_code"


class InvalidMoneyError(DomainError):
    """Money and scalar operands must be finite exact decimals."""

    code = "invalid_money"


class CurrencyMismatchError(DomainError):
    """Arithmetic across currencies requires an explicit conversion."""

    code = "currency_mismatch"


class InexactMoneyDivisionError(InvalidMoneyError):
    """A repeating decimal requires an explicit calculation precision."""

    code = "inexact_money_division"

from src.modules.shared.domain.domain_error import DomainError


class InvalidMoneyError(DomainError):
    """Сумма или валюта денег не соответствует контракту хранения."""


class MoneyCurrencyMismatchError(DomainError):
    """Арифметика денег требует одинаковой валюты обоих операндов."""

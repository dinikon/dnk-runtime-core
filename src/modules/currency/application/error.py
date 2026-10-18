class ExchangeRateCatalogMismatchError(Exception):
    """Numeric-код котировки не совпадает с активным валютным справочником."""


class ExchangeRateSourceError(Exception):
    """Внешний источник не предоставил пригодный полный ответ."""

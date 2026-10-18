from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetCurrencyValidationCatalogQuery:
    """Запрашивает активные справочные сведения для конкретного набора кодов."""

    codes: tuple[str, ...]

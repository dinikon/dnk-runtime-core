from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListDealCurrenciesQuery:
    """Пустой вход read-only справочника CRM."""

from dataclasses import dataclass
from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey


@dataclass(frozen=True, slots=True)
class SearchCounterpartyReferencesQuery:
    """Задаёт тип контрагента, серверный поиск и страницу выбора."""

    model_key: CounterpartyModelKey
    search: str | None = None
    offset: int = 0
    limit: int = 20

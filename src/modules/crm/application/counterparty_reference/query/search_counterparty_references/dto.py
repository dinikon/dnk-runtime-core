from dataclasses import dataclass
from src.modules.crm.application.counterparty_reference.dto import (
    CounterpartyReferenceDTO,
)


@dataclass(frozen=True, slots=True)
class SearchCounterpartyReferencesResultDTO:
    """Страница публичных ссылок на компании или контакты."""

    items: tuple[CounterpartyReferenceDTO, ...]
    total: int
    offset: int
    limit: int

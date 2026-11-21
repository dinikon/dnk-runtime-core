from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class CounterpartyModelKey(StrEnum):
    """Публичные ключи поддерживаемых контрагентов CRM."""

    COMPANY = "crm.company"
    CONTACT = "crm.contact"


@dataclass(frozen=True, slots=True)
class CounterpartyReferenceDTO:
    """Передаёт тип, UUID и отображаемое имя контрагента без его агрегата."""

    model_key: CounterpartyModelKey
    id: UUID
    display_name: str

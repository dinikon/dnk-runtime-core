from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConvertLeadResultDTO:
    """Идентификаторы действительно созданных объектов и аудит результата."""

    conversion_id: str
    mode: str
    contact_id: str | None
    company_id: str | None
    deal_id: str | None
    basket_id: str | None
    converted_at: str
    converted_by: str
    replay: bool = False

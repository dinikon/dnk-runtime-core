from typing import Self
from uuid import UUID
from pydantic import BaseModel
from src.modules.crm.application.counterparty_reference.dto import CounterpartyModelKey
from src.modules.crm.application.counterparty_reference.query.search_counterparty_references.dto import (
    SearchCounterpartyReferencesResultDTO,
)


class SearchCounterpartyReferenceItemResponse(BaseModel):
    """Публичная составная ссылка и имя компании либо контакта."""

    model_key: CounterpartyModelKey
    id: UUID
    display_name: str


class SearchCounterpartyReferencesResponse(BaseModel):
    """HTTP-страница выбора контрагента."""

    items: list[SearchCounterpartyReferenceItemResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: SearchCounterpartyReferencesResultDTO) -> Self:
        """Явно преобразует конкретный результат поиска в HTTP."""
        return cls(
            items=[
                SearchCounterpartyReferenceItemResponse(
                    model_key=item.model_key, id=item.id, display_name=item.display_name
                )
                for item in dto.items
            ],
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )

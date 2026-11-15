from datetime import date
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.list_receipt_references.dto import ListReceiptReferencesResultDTO
class ReceiptReferenceItemResponse(BaseModel):
    """Сериализует выбор и календарные даты исключительно из партии."""
    id:UUID
    label:str
    lot_id:UUID|None
    lot_number:str|None
    manufactured_on:date|None
    expires_on:date|None
class ListReceiptReferencesResponse(BaseModel):
    """Возвращает страницу вариантов приёмки."""
    items:list[ReceiptReferenceItemResponse]
    total:int
    offset:int
    limit:int
    @classmethod
    def from_dto(cls,dto:ListReceiptReferencesResultDTO)->"ListReceiptReferencesResponse":
        """Преобразует конкретную проекцию без timezone-преобразования календарных дат."""
        return cls(items=[ReceiptReferenceItemResponse(id=v.id,label=v.label,lot_id=v.lot_id,lot_number=v.lot_number,manufactured_on=v.manufactured_on,expires_on=v.expires_on) for v in dto.items],total=dto.total,offset=dto.offset,limit=dto.limit)

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.list_receipt_executions.dto import ListReceiptExecutionsResultDTO
class ListReceiptExecutionItemResponse(BaseModel):
    """Показывает факт и статус на момент его проведения."""
    execution_id:UUID
    posting_id:UUID
    posted_at:datetime
    document_version_after:int
    document_status:str
    line_count:int
class ListReceiptExecutionsResponse(BaseModel):
    """Сериализует страницу истории документа."""
    items:list[ListReceiptExecutionItemResponse]
    total:int
    offset:int
    limit:int
    @classmethod
    def from_dto(cls,dto:ListReceiptExecutionsResultDTO)->"ListReceiptExecutionsResponse":
        """Явно преобразует собственный результат чтения."""
        return cls(items=[ListReceiptExecutionItemResponse(execution_id=v.execution_id,posting_id=v.posting_id,posted_at=v.posted_at,document_version_after=v.document_version_after,
            document_status=v.document_status,line_count=v.line_count) for v in dto.items],total=dto.total,offset=dto.offset,limit=dto.limit)

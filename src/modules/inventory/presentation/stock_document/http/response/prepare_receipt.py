from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.prepare_receipt.dto import PrepareReceiptResultDTO
class PrepareReceiptLineResponse(BaseModel):
    """Передаёт числовое основание и актуальные режимы одной строки."""
    document_line_id:UUID
    inventory_item_id:UUID
    sku:str
    base_uom:str
    current_base_uom:str
    remaining_quantity:Decimal
    quantity_step:Decimal
    tracking_mode:str
    expiration_mode:str
class PrepareReceiptResponse(BaseModel):
    """Сериализует точный остаток плана для формы приёмки."""
    document_id:UUID
    version:int
    status:str
    warehouse_id:UUID
    default_storage_location_id:UUID|None
    lines:list[PrepareReceiptLineResponse]
    @classmethod
    def from_dto(cls,dto:PrepareReceiptResultDTO)->"PrepareReceiptResponse":
        """Явно преобразует собственный DTO без текущих цен и чисел floating point."""
        return cls(document_id=dto.document_id,version=dto.version,status=dto.status,warehouse_id=dto.warehouse_id,default_storage_location_id=dto.default_storage_location_id,
            lines=[PrepareReceiptLineResponse(document_line_id=v.document_line_id,inventory_item_id=v.inventory_item_id,sku=v.sku,base_uom=v.base_uom,current_base_uom=v.current_base_uom,
                remaining_quantity=v.remaining_quantity,quantity_step=v.quantity_step,tracking_mode=v.tracking_mode,expiration_mode=v.expiration_mode) for v in dto.lines])

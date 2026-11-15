from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID
@dataclass(frozen=True, slots=True)
class PrepareReceiptLineDTO:
    """Передаёт точный остаток плана и актуальные настройки выбора прослеживаемости."""
    document_line_id:UUID
    inventory_item_id:UUID
    sku:str
    base_uom:str
    current_base_uom:str
    remaining_quantity:Decimal
    quantity_step:Decimal
    tracking_mode:str
    expiration_mode:str
@dataclass(frozen=True, slots=True)
class PrepareReceiptResultDTO:
    """Возвращает серверное основание формы приёмки с версией документа."""
    document_id:UUID
    version:int
    status:str
    warehouse_id:UUID
    default_storage_location_id:UUID|None
    lines:tuple[PrepareReceiptLineDTO,...]

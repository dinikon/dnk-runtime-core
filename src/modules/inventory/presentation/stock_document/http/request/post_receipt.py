from typing import Annotated,Literal,Self
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,StrictStr,StrictInt,model_validator
from src.modules.inventory.domain.value_object.stock_status import StockStatus

class ReceiptActualLineRequest(BaseModel):
    """Принимает только фактические назначения собственной строки плана."""
    model_config=ConfigDict(extra="forbid")
    client_line_id:UUID
    document_line_id:UUID
    quantity:Annotated[StrictStr,Field(max_length=128,pattern=r"^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$")]
    uom:Annotated[StrictStr,Field(min_length=1,max_length=16)]
    location_id:UUID
    lot_id:UUID|None=None
    serial_id:UUID|None=None
    stock_status:StockStatus=StockStatus.SELLABLE

class ReceiptCostAllocationRequest(BaseModel):
    """Связывает сумму с существующим ключом фактической строки запроса."""
    model_config=ConfigDict(extra="forbid")
    client_line_id:UUID
    amount:Annotated[StrictStr,Field(max_length=40,pattern=r"^[0-9]+(?:\.[0-9]{1,4})?$")]

class ReceiptCostRequest(BaseModel):
    """Отличает известную сумму, включая ноль, от отсутствующего основания."""
    model_config=ConfigDict(extra="forbid")
    amount:Annotated[StrictStr,Field(max_length=40,pattern=r"^[0-9]+(?:\.[0-9]{1,4})?$")]
    currency:Annotated[StrictStr,Field(min_length=3,max_length=3)]
    basis_kind:Literal["MANUAL","EXTERNAL"]="MANUAL"
    source_system:Annotated[StrictStr,Field(min_length=1,max_length=200)]|None=None
    source_reference:Annotated[StrictStr,Field(min_length=1,max_length=200)]|None=None
    allocations:list[ReceiptCostAllocationRequest]=Field(default_factory=list,max_length=500)

class PostReceiptRequest(BaseModel):
    """Проверяет ограниченный размер команды и форму ссылок до Application."""
    model_config=ConfigDict(extra="forbid")
    expected_version:StrictInt=Field(ge=0)
    lines:list[ReceiptActualLineRequest]=Field(min_length=1,max_length=500)
    costs:list[ReceiptCostRequest]=Field(default_factory=list,max_length=500)
    @model_validator(mode="after")
    def consistent_client_keys(self)->Self:
        """Отклоняет повтор ключа строки и ссылки стоимости за пределы текущего запроса."""
        keys=[line.client_line_id for line in self.lines]
        if len(keys)!=len(set(keys)):raise ValueError("Ключ фактической строки должен быть уникальным.")
        for cost in self.costs:
            ids=[allocation.client_line_id for allocation in cost.allocations]
            if len(ids)!=len(set(ids)) or not set(ids)<=set(keys):raise ValueError("Распределение ссылается на повторную или неизвестную строку запроса.")
        return self

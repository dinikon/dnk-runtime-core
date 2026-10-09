from pydantic import BaseModel, ConfigDict


class CreateWarehousePolicyRequest(BaseModel):
    """HTTP-настройки создания склада: только обязательный timezone."""

    model_config = ConfigDict(extra="forbid", strict=True)
    timezone: str


class CreateWarehouseRequest(BaseModel):
    """Самостоятельный HTTP-контракт POST, без tenant, actor, status и revision."""

    model_config = ConfigDict(extra="forbid", strict=True)
    code: str
    title: str
    type: str
    policy: CreateWarehousePolicyRequest

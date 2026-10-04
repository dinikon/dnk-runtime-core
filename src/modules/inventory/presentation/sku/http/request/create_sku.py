from pydantic import BaseModel, ConfigDict


class CreateSkuRequest(BaseModel):
    """HTTP-поля создания без возможности подменить ID, tenant или аудит."""

    model_config = ConfigDict(extra="forbid", strict=True)

    code: str
    title: str

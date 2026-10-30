from pydantic import BaseModel, ConfigDict, Field


class RequestContentDeliveryRequest(BaseModel):
    """Подтверждает версии сохранённого представления и проверенный preview."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(gt=0, strict=True)
    expected_binding_revision: int = Field(gt=0, strict=True)
    expected_config_revision: int = Field(gt=0, strict=True)
    content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

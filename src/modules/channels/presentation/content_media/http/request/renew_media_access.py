from pydantic import BaseModel, ConfigDict, Field


class RenewMediaAccessRequest(BaseModel):
    """Явный контракт renew_media_access с проверкой ожидаемой ревизии."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, strict=True)

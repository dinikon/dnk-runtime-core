from pydantic import BaseModel, ConfigDict, Field


class RevokeMediaAccessRequest(BaseModel):
    """Явный контракт revoke_media_access с проверкой ожидаемой ревизии."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, strict=True)

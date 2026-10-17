from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PutContactContactPointDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    value: str
    binding_id: UUID | None = None
    label_id: UUID | None = None
    country_code: str | None = None


class PutContactContactPointsRequest(BaseModel):
    """Полная замена контактных данных contact."""

    model_config = ConfigDict(extra="forbid", strict=True)

    phones: list[PutContactContactPointDraftRequest]
    emails: list[PutContactContactPointDraftRequest]

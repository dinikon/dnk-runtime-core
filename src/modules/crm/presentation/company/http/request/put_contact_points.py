from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PutCompanyContactPointDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    value: str
    binding_id: UUID | None = None
    label_id: UUID | None = None
    country_code: str | None = None


class PutCompanyContactPointsRequest(BaseModel):
    """Полная замена контактных данных company."""

    model_config = ConfigDict(extra="forbid", strict=True)

    phones: list[PutCompanyContactPointDraftRequest]
    emails: list[PutCompanyContactPointDraftRequest]

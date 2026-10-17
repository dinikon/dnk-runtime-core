from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class PatchContactContactPointDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    value: str
    binding_id: UUID | None = None
    label_id: UUID | None = None
    country_code: str | None = None


class PatchContactContactPointsRequest(BaseModel):
    """Частичное изменение контактных данных contact."""

    model_config = ConfigDict(extra="forbid", strict=True)

    phones: list[PatchContactContactPointDraftRequest] | None = None
    emails: list[PatchContactContactPointDraftRequest] | None = None

    @model_validator(mode="after")
    def reject_null_arrays(self):
        for field in ("phones", "emails"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} must be an array")
        return self

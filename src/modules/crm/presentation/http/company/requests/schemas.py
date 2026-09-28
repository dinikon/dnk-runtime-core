from uuid import UUID
from pydantic import Field, model_validator
from pydantic import ConfigDict
from src.modules.crm.presentation.http.contact_points import ContactPointsRequest


class CreateCompanyRequest(ContactPointsRequest):
    """HTTP-поля создания компании."""

    model_config = ConfigDict(extra="forbid")

    name: str

    contact_ids: list[UUID] = Field(default_factory=list)


class UpdateCompanyRequest(CreateCompanyRequest):
    """HTTP-поля полного обновления компании."""

    expected_contact_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_original_links(self):
        if ("contact_ids" in self.model_fields_set) != (
            "expected_contact_ids" in self.model_fields_set
        ):
            raise ValueError("Передайте новый и исходный списки связей вместе.")
        return self


__all__ = ["CreateCompanyRequest", "UpdateCompanyRequest"]

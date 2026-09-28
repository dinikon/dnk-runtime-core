from uuid import UUID
from pydantic import Field, model_validator
from pydantic import ConfigDict
from src.modules.crm.presentation.http.contact_points import ContactPointsRequest


class CreateContactRequest(ContactPointsRequest):
    """HTTP-поля создания контакта."""

    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None

    company_ids: list[UUID] = Field(default_factory=list)


class UpdateContactRequest(CreateContactRequest):
    """HTTP-поля полного обновления контакта."""

    expected_company_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_original_links(self):
        if ("company_ids" in self.model_fields_set) != (
            "expected_company_ids" in self.model_fields_set
        ):
            raise ValueError("Передайте новый и исходный списки связей вместе.")
        return self


__all__ = ["CreateContactRequest", "UpdateContactRequest"]

from pydantic import ConfigDict
from src.modules.crm.presentation.http.contact_points import ContactPointsRequest


class CreateContactRequest(ContactPointsRequest):
    """HTTP-поля создания контакта."""

    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None


class UpdateContactRequest(CreateContactRequest):
    """HTTP-поля полного обновления контакта."""


__all__ = ["CreateContactRequest", "UpdateContactRequest"]

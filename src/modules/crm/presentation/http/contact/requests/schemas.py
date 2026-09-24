from pydantic import BaseModel, ConfigDict


class CreateContactRequest(BaseModel):
    """HTTP-поля создания контакта."""

    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None


class UpdateContactRequest(CreateContactRequest):
    """HTTP-поля полного обновления контакта."""


__all__ = ["CreateContactRequest", "UpdateContactRequest"]

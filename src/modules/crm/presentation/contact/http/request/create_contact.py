from pydantic import BaseModel, ConfigDict


class CreateContactRequest(BaseModel):
    """Исходное ФИО нового контакта."""

    model_config = ConfigDict(extra="forbid", strict=True)

    first_name: str
    last_name: str | None = None
    middle_name: str | None = None

from pydantic import BaseModel, ConfigDict


class CreateContactRequest(BaseModel):
    """Принимает только исходное ФИО; контекст и аудит поступают с сервера."""

    model_config = ConfigDict(extra="forbid", strict=True)

    first_name: str
    last_name: str
    middle_name: str | None = None

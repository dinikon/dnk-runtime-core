from pydantic import BaseModel, ConfigDict, model_validator


class CreateContactRequest(BaseModel):
    """Принимает только исходное ФИО; контекст и аудит поступают с сервера."""

    model_config = ConfigDict(extra="forbid", strict=True)

    first_name: str
    last_name: str
    middle_name: str | None = None


class PutContactRequest(BaseModel):
    """Полная замена ФИО; отчество можно опустить для значения null."""

    model_config = ConfigDict(extra="forbid", strict=True)

    first_name: str
    last_name: str
    middle_name: str | None = None


class PatchContactRequest(BaseModel):
    """Изменяет только явно переданные части ФИО."""

    model_config = ConfigDict(extra="forbid", strict=True)

    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None

    @model_validator(mode="after")
    def require_changes(self) -> "PatchContactRequest":
        if not self.model_fields_set:
            raise ValueError("At least one name field is required.")
        return self

from pydantic import BaseModel, ConfigDict


class CreateCompanyRequest(BaseModel):
    """HTTP-поля создания компании."""

    model_config = ConfigDict(extra="forbid")

    name: str


class UpdateCompanyRequest(CreateCompanyRequest):
    """HTTP-поля полного обновления компании."""


__all__ = ["CreateCompanyRequest", "UpdateCompanyRequest"]

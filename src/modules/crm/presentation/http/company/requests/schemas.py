from pydantic import ConfigDict
from src.modules.crm.presentation.http.contact_points import ContactPointsRequest


class CreateCompanyRequest(ContactPointsRequest):
    """HTTP-поля создания компании."""

    model_config = ConfigDict(extra="forbid")

    name: str


class UpdateCompanyRequest(CreateCompanyRequest):
    """HTTP-поля полного обновления компании."""


__all__ = ["CreateCompanyRequest", "UpdateCompanyRequest"]

from uuid import UUID
from pydantic import BaseModel
from src.modules.crm.presentation.lead.http.response.get_lead import GetLeadResponse


class ConversionCompanyResponse(BaseModel):
    """Доступная существующая компания исходного контакта."""

    id: UUID
    legal_name: str


class GetLeadConversionContextResponse(BaseModel):
    """Подготовка формы без записи и фиктивных результатов."""

    source_token: str
    source: GetLeadResponse
    available_companies: tuple[ConversionCompanyResponse, ...]
    modes: tuple[str, ...]

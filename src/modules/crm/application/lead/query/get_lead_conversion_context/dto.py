from dataclasses import dataclass
from src.modules.crm.application.lead.port.read_row import LeadReadRowDTO
from src.modules.crm.application.basket.values import OwnerBasketProjection
from src.modules.crm.application.contact_point.dto import ContactPointsDTO
from src.modules.crm.application.company.query.get_company.dto import CompanyDetailsDTO


@dataclass(frozen=True, slots=True)
class GetLeadConversionContextResultDTO:
    """Проверяемый снимок источника и кандидатов для формы конвертации."""

    source_token: str
    record: LeadReadRowDTO
    basket: OwnerBasketProjection
    points: ContactPointsDTO
    available_companies: tuple[CompanyDetailsDTO, ...]
    modes: tuple[str, ...]

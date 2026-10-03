from dataclasses import dataclass

from src.modules.crm.application.company.query.get_company.dto import CompanyDetailsDTO


@dataclass(frozen=True, slots=True)
class ListCompaniesResultDTO:
    companies: tuple[CompanyDetailsDTO, ...]

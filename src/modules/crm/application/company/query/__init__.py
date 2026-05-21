from src.modules.crm.application.company.query.describe_company_fields_repository import (
    CompanyFieldsDescriptionRepositoryProtocol,
)
from src.modules.crm.application.company.query.get_company_query import GetCompanyQuery
from src.modules.crm.application.company.query.list_companies_query import (
    ListCompaniesQuery,
)
from src.modules.crm.application.company.query.repository import (
    CompanyQueryRepositoryProtocol,
)

__all__ = [
    "CompanyFieldsDescriptionRepositoryProtocol",
    "CompanyQueryRepositoryProtocol",
    "GetCompanyQuery",
    "ListCompaniesQuery",
]

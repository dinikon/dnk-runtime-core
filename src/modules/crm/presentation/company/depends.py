from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.company.command.create_company.handler import (
    CreateCompanyHandler,
)
from src.modules.crm.application.company.command.delete_company.handler import (
    DeleteCompanyHandler,
)
from src.modules.crm.application.company.command.update_company.handler import (
    UpdateCompanyHandler,
)
from src.modules.crm.application.company.port.query_repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.application.company.query.get_company.handler import (
    GetCompanyHandler,
)
from src.modules.crm.application.company.query.list_companies.handler import (
    ListCompaniesHandler,
)
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.crm.infrastructure.company.persistence.query_repository import (
    SqlAlchemyCompanyQueryRepository,
)
from src.modules.crm.infrastructure.company.persistence.repository import (
    SqlAlchemyCompanyRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_company_repository(uow: UoWDep) -> CompanyRepositoryProtocol:
    return SqlAlchemyCompanyRepository(uow.session)


CompanyRepositoryDep = Annotated[
    CompanyRepositoryProtocol, Depends(get_company_repository)
]


def get_company_query_repository(uow: UoWDep) -> CompanyQueryRepositoryProtocol:
    return SqlAlchemyCompanyQueryRepository(uow.session)


CompanyQueryRepositoryDep = Annotated[
    CompanyQueryRepositoryProtocol, Depends(get_company_query_repository)
]


def get_create_company_handler(
    repository: CompanyRepositoryDep, clock: ClockDep, uuid_generator: UuidDep
) -> CreateCompanyHandler:
    return CreateCompanyHandler(repository, clock, uuid_generator)


CreateCompanyHandlerDep = Annotated[
    CreateCompanyHandler, Depends(get_create_company_handler)
]


def get_get_company_handler(
    repository: CompanyQueryRepositoryDep,
) -> GetCompanyHandler:
    return GetCompanyHandler(repository)


GetCompanyHandlerDep = Annotated[GetCompanyHandler, Depends(get_get_company_handler)]


def get_list_companies_handler(
    repository: CompanyQueryRepositoryDep,
) -> ListCompaniesHandler:
    return ListCompaniesHandler(repository)


ListCompaniesHandlerDep = Annotated[
    ListCompaniesHandler, Depends(get_list_companies_handler)
]


def get_update_company_handler(
    repository: CompanyRepositoryDep, clock: ClockDep
) -> UpdateCompanyHandler:
    return UpdateCompanyHandler(repository, clock)


UpdateCompanyHandlerDep = Annotated[
    UpdateCompanyHandler, Depends(get_update_company_handler)
]


def get_delete_company_handler(
    repository: CompanyRepositoryDep,
) -> DeleteCompanyHandler:
    return DeleteCompanyHandler(repository)


DeleteCompanyHandlerDep = Annotated[
    DeleteCompanyHandler, Depends(get_delete_company_handler)
]

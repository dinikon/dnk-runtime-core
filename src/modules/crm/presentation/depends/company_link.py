from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.contact.command.link_company.handler import (
    LinkCompanyHandler,
)
from src.modules.crm.application.contact.command.unlink_company.handler import (
    UnlinkCompanyHandler,
)
from src.modules.crm.application.contact.port.company_link_repository import (
    CompanyLinkRepositoryProtocol,
)
from src.modules.crm.infrastructure.contact.persistence.company_link_repository import (
    SqlAlchemyCompanyLinkRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_company_link_repository(uow: UoWDep) -> CompanyLinkRepositoryProtocol:
    return SqlAlchemyCompanyLinkRepository(uow.session)


CompanyLinkRepositoryDep = Annotated[
    CompanyLinkRepositoryProtocol, Depends(get_company_link_repository)
]


def get_link_company_handler(
    repository: CompanyLinkRepositoryDep,
) -> LinkCompanyHandler:
    return LinkCompanyHandler(repository)


LinkCompanyHandlerDep = Annotated[LinkCompanyHandler, Depends(get_link_company_handler)]


def get_unlink_company_handler(
    repository: CompanyLinkRepositoryDep,
) -> UnlinkCompanyHandler:
    return UnlinkCompanyHandler(repository)


UnlinkCompanyHandlerDep = Annotated[
    UnlinkCompanyHandler, Depends(get_unlink_company_handler)
]

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.domain.contact.repository import (
    ContactCommandRepositoryProtocol,
)


def get_contact_query_repository() -> ContactQueryRepositoryProtocol:
    raise NotImplementedError("CRM contact query repository is not configured.")


ContactQueryRepositoryDep = Annotated[
    ContactQueryRepositoryProtocol,
    Depends(get_contact_query_repository),
]


def get_contact_command_repository() -> ContactCommandRepositoryProtocol:
    raise NotImplementedError("CRM contact command repository is not configured.")


ContactCommandRepositoryDep = Annotated[
    ContactCommandRepositoryProtocol,
    Depends(get_contact_command_repository),
]


__all__ = [
    "ContactCommandRepositoryDep",
    "ContactQueryRepositoryDep",
    "get_contact_command_repository",
    "get_contact_query_repository",
]

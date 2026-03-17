from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.crm.domain.contact.repository import (
    ContactCommandRepositoryProtocol,
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.infrastructure import (
    FakeContactCommandRepository,
    FakeContactQueryRepository,
    get_fake_contacts_storage,
)


def get_contact_query_repository() -> ContactQueryRepositoryProtocol:
    return FakeContactQueryRepository(get_fake_contacts_storage())


ContactQueryRepositoryDep = Annotated[
    ContactQueryRepositoryProtocol,
    Depends(get_contact_query_repository),
]


def get_contact_command_repository() -> ContactCommandRepositoryProtocol:
    return FakeContactCommandRepository(get_fake_contacts_storage())


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

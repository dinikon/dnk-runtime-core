from typing import Protocol

from modules.crm.application.contact import ListContactsQueryDTO
from modules.crm.application.contact.dto.contact_list_dto import ContactListDTO
from modules.crm.domain.contact.repository import ContactRepositoryPort


class ListContactUseCaseProtocol(Protocol):
    def execute(self, query: ListContactsQueryDTO) -> ContactListDTO: ...


class ListContactUseCaseImpl:

    def __init__(self): ...

    def execute(self, query: ListContactsQueryDTO) -> ContactListDTO: ...

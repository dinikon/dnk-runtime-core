from typing import Protocol

from modules.crm.application.contact import AddContactCommandDTO, ContactDTO


class AddContactUseCaseProtocol(Protocol):
    def execute(self, command: AddContactCommandDTO) -> ContactDTO: ...


class AddContactUseCase:

    def __init__(self): ...

    async def execute(self, command: AddContactCommandDTO) -> ContactDTO: ...

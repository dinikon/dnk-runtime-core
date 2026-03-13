from typing import Protocol

from modules.crm.application.contact import UpdateContactCommandDTO, ContactDTO


class UpdateContactUseCaseProtocol(Protocol):
    async def execute(self, command: UpdateContactCommandDTO) -> ContactDTO: ...


class UpdateContactUseCase:

    def __init__(self): ...

    async def execute(self, command: UpdateContactCommandDTO) -> ContactDTO: ...

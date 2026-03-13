from typing import Protocol

from modules.crm.application.contact import GetContactQueryDTO, ContactDTO


class GetContactUseCaseProtocol(Protocol):
    async def execute(self, query: GetContactQueryDTO) -> ContactDTO: ...


class GetContactUseCase:

    def __init__(self): ...

    async def execute(self, query: GetContactQueryDTO) -> ContactDTO: ...

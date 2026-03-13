from typing import Protocol

from modules.crm.application.contact import DeleteContactCommandDTO


class DeleteContactUseCaseProtocol(Protocol):
    async def execute(self, command: DeleteContactCommandDTO) -> None: ...


class DeleteContactUseCase:

    def __init__(self): ...

    async def execute(self, command: DeleteContactCommandDTO) -> None: ...

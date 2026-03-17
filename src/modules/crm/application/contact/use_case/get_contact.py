from typing import Protocol


class GetContactUseCaseProtocol(Protocol):
    async def __call__(self, *, contact_id: str) -> None: ...

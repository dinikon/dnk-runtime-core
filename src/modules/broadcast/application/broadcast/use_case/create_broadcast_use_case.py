import uuid
from datetime import datetime
from typing import Protocol

from src.modules.broadcast.application.broadcast.command.create_broadcast import (
    CreateBroadcastCommand,
)
from src.modules.broadcast.application.broadcast.dto.broadcast_dto import BroadcastDTO


class CreateBroadcastUseCaseProtocol(Protocol): ...


class CreateBroadcastUseCase:
    def __init__(self) -> None: ...

    def __call__(self, command: CreateBroadcastCommand) -> BroadcastDTO:
        return BroadcastDTO(
            id=uuid.uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            title=command.title,
            description=command.description,
            status="draft",
        )

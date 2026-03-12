from __future__ import annotations

from src.modules.runtime_schema.application.object_definition.dto import (
    CreateObjectCommandDTO,
    DeleteObjectCommandDTO,
    ObjectDefinitionDTO,
    UpdateObjectCommandDTO,
)
from src.modules.runtime_schema.application.ports.orchestrator import (
    DdlOrchestratorServiceProtocol,
)


class CreateObjectDefinitionUseCase:
    def __init__(self, orchestrator: DdlOrchestratorServiceProtocol):
        self._orchestrator = orchestrator

    async def execute(self, dto: CreateObjectCommandDTO) -> ObjectDefinitionDTO:
        return await self._orchestrator.create_object_definition(dto=dto)


class UpdateObjectDefinitionUseCase:
    def __init__(self, orchestrator: DdlOrchestratorServiceProtocol):
        self._orchestrator = orchestrator

    async def execute(self, dto: UpdateObjectCommandDTO) -> ObjectDefinitionDTO:
        return await self._orchestrator.update_object_definition(dto=dto)


class DeleteObjectDefinitionUseCase:
    def __init__(self, orchestrator: DdlOrchestratorServiceProtocol):
        self._orchestrator = orchestrator

    async def execute(self, dto: DeleteObjectCommandDTO) -> None:
        await self._orchestrator.delete_object_definition(dto=dto)


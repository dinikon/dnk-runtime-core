from __future__ import annotations

from src.modules.runtime_schema.application.field_definition.dto import (
    CreateFieldCommandDTO,
    DeleteFieldCommandDTO,
    FieldDefinitionDTO,
    UpdateFieldCommandDTO,
)
from src.modules.runtime_schema.application.ports.orchestrator import (
    DdlOrchestratorServiceProtocol,
)


class CreateFieldDefinitionUseCase:
    def __init__(self, orchestrator: DdlOrchestratorServiceProtocol):
        self._orchestrator = orchestrator

    async def execute(self, dto: CreateFieldCommandDTO) -> FieldDefinitionDTO:
        return await self._orchestrator.create_field_definition(dto=dto)


class UpdateFieldDefinitionUseCase:
    def __init__(self, orchestrator: DdlOrchestratorServiceProtocol):
        self._orchestrator = orchestrator

    async def execute(self, dto: UpdateFieldCommandDTO) -> FieldDefinitionDTO:
        return await self._orchestrator.update_field_definition(dto=dto)


class DeleteFieldDefinitionUseCase:
    def __init__(self, orchestrator: DdlOrchestratorServiceProtocol):
        self._orchestrator = orchestrator

    async def execute(self, dto: DeleteFieldCommandDTO) -> None:
        await self._orchestrator.delete_field_definition(dto=dto)


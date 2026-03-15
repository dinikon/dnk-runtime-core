from typing import Protocol

from modules.runtime_schema.application.schema.command.create_schema import (
    CreateSchemaCommandDTO,
)
from modules.runtime_schema.application.schema.dto.schema_dto import SchemaDTO


class CreateSchemaUseCaseProtocol(Protocol):
    async def execute(self, command: CreateSchemaCommandDTO) -> SchemaDTO: ...


class CreateSchemaUseCaseImpl:
    def __init__(self): ...

    async def execute(self, command: CreateSchemaCommandDTO) -> SchemaDTO: ...

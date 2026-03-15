from __future__ import annotations

from typing import Callable, Protocol
from uuid import UUID, uuid4

from src.modules.runtime_schema.domain.data_source.value_object.schama_name import (
    SchemaNameVO,
)


class SchemaNameServiceProtocol(Protocol):
    def build_schema_name(self, schema_id: UUID) -> SchemaNameVO: ...

    def generate_schema_name(self) -> SchemaNameVO: ...


class SchemaNameService:
    def __init__(
        self,
        schema_prefix: str,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._schema_prefix = schema_prefix
        self._uuid_factory = uuid_factory or uuid4

    def build_schema_name(self, schema_id: UUID) -> SchemaNameVO:
        # Use hex UUID to satisfy SchemaNameVO (only a-z0-9_ allowed).
        return SchemaNameVO(f"{self._schema_prefix}{schema_id.hex}")

    def generate_schema_name(self) -> SchemaNameVO:
        return self.build_schema_name(self._uuid_factory())

from typing import Protocol

from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class SeedReaderPort(Protocol):
    async def read(self, *, seed_path: str) -> SchemaSeed: ...

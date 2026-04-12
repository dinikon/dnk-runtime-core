from typing import Protocol

from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class SeedReaderPort(Protocol):
    """Порт чтения seed-спеки из внешнего источника."""

    async def read(self, *, seed_path: str) -> SchemaSeed:
        """Загружает seed по dotted-path или другому поддержанному адресу."""
        ...

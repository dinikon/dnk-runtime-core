from __future__ import annotations

import importlib

from src.modules.schema_registry.application.ports.seed_reader import SeedReaderPort
from src.modules.schema_registry.domain.error import SeedValidationError
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class PythonModuleSeedReader(SeedReaderPort):
    async def read(self, *, seed_path: str) -> SchemaSeed:
        normalized = seed_path.strip()
        if not normalized:
            raise SeedValidationError("Seed module path must not be empty.")

        try:
            module = importlib.import_module(normalized)
        except ModuleNotFoundError as exc:
            raise SeedValidationError(
                f"Seed module '{normalized}' was not found."
            ) from exc

        seed = getattr(module, "SCHEMA_SEED", None)
        if seed is None:
            raise SeedValidationError(
                f"Seed module '{normalized}' must expose SCHEMA_SEED."
            )
        if not isinstance(seed, SchemaSeed):
            raise SeedValidationError("SCHEMA_SEED must be an instance of SchemaSeed.")
        return seed

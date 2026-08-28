from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed

SCHEMA_SEED = SchemaSeed(
    version=None,
    code="runtime",
    label="Runtime",
    objects=(),
)


__all__ = ["SCHEMA_SEED"]

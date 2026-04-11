from pydantic import Field
from pydantic_settings import BaseSettings


class RuntimeSchema(BaseSettings):
    SCHEMA_PREFIX: str = Field(
        default="dnk_",
        min_length=4,
        max_length=10,
        description="Prefix for runtime schema names.",
    )
    DEFAULT_SEED_MODULE: str = Field(
        default="src.modules.schema_registry.seed.schema_seed",
        min_length=1,
        description="Python module path that exposes SCHEMA_SEED for bootstrap.",
    )

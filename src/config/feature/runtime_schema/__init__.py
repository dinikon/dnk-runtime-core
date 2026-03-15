from pydantic import Field
from pydantic_settings import BaseSettings


class RuntimeSchema(BaseSettings):
    SCHEMA_PREFIX: str = Field(
        default="dnk_",
        min_length=4,
        max_length=10,
        description="Prefix for runtime schema names.",
    )

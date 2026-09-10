from pydantic import Field
from pydantic_settings import BaseSettings


class TenantSchema(BaseSettings):
    """Настройки именования PostgreSQL-схем tenants."""

    SCHEMA_PREFIX: str = Field(
        default="dnk_",
        min_length=4,
        max_length=10,
        pattern=r"^[a-z_][a-z0-9_]*$",
        description="Stable prefix for tenant schema names.",
    )

from pydantic import Field
from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    REDIS_HOST: str = Field(
        default="localhost",
        description="Redis server host.",
    )
    REDIS_PORT: int = Field(
        default=6379,
        ge=1,
        description="Redis server port.",
    )
    REDIS_USERNAME: str = Field(
        default="",
        description="Redis username.",
    )
    REDIS_PASSWORD: str = Field(
        default="",
        description="Redis password.",
    )
    REDIS_USE_SSL: bool = Field(
        default=False,
        description="Whether to use SSL for Redis connection.",
    )
    REDIS_DB: int = Field(
        default=0,
        ge=0,
        description="Redis logical database index.",
    )

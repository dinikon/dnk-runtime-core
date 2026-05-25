from __future__ import annotations

from pydantic import BaseModel, Field, PositiveInt
from pydantic_settings import BaseSettings


class RabbitMQSettings(BaseModel):
    enabled: bool = Field(default=False)
    url: str = Field(default="amqp://guest:guest@localhost:5672/")
    publisher_confirms: bool = Field(default=True)
    prefetch: PositiveInt = Field(default=20)


class RabbitMQConfig(BaseSettings):
    RABBITMQ: RabbitMQSettings = Field(default_factory=RabbitMQSettings)


__all__ = [
    "RabbitMQConfig",
    "RabbitMQSettings",
]

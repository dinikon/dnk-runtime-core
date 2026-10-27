from typing import Literal
from pydantic import BaseModel, Field, SecretStr
from src.modules.channels.infrastructure.platforms.base import StrictModel


class PromSettings(StrictModel):
    """В первом срезе дополнительных настроек Prom нет."""


class PromConfig(StrictModel):
    """Фиксированный endpoint публичного API Prom."""

    version: Literal[1] = 1
    endpoint: Literal["https://my.prom.ua"] = "https://my.prom.ua"
    settings: PromSettings = Field(default_factory=PromSettings)


class PromCredentials(StrictModel):
    """Токен доступа к API магазина."""

    token: SecretStr = Field(min_length=1, max_length=4096, title="Токен доступа")


class PromGroup(BaseModel):
    """Минимальная часть ответа groups/list для определения корневой группы."""

    id: int = Field(strict=True)
    parent_group_id: int | None = Field(strict=True)


class PromGroups(BaseModel):
    """Страница групп; отсутствие groups не считается пустым магазином."""

    groups: list[PromGroup]

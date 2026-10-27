from typing import Literal
from pydantic import BaseModel, Field, SecretStr
from src.modules.channels.infrastructure.platforms.base import StrictModel


class RozetkaSettings(StrictModel):
    """Логин пользователя кабинета продавца."""

    username: str = Field(min_length=1, max_length=255, title="Логин продавца")


class RozetkaConfig(StrictModel):
    """Конфигурация API Rozetka."""

    version: Literal[1] = 1
    endpoint: Literal["https://api-seller.rozetka.com.ua"] = (
        "https://api-seller.rozetka.com.ua"
    )
    settings: RozetkaSettings


class RozetkaCredentials(StrictModel):
    """Пароль кабинета хранится только зашифрованным."""

    password: SecretStr = Field(min_length=1, max_length=4096, title="Пароль")


class RozetkaMarket(BaseModel):
    """Identity магазина, а не пользователя кабинета."""

    id: int = Field(gt=0, strict=True)


class RozetkaContent(BaseModel):
    """Сохраняется только identity; временный access_token игнорируется."""

    market: RozetkaMarket


class RozetkaLogin(BaseModel):
    """Успешный ответ sites должен содержать market."""

    success: bool = Field(strict=True)
    content: RozetkaContent | None = None

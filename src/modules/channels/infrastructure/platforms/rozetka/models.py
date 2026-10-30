from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

from src.modules.channels.infrastructure.platforms.base import (
    StrictModel,
    StockSyncSettings,
)


class RozetkaSettings(StrictModel):
    """Фиксированные валюта и языки площадки."""

    stock_sync: StockSyncSettings = Field(default_factory=StockSyncSettings)

    currency: Literal["UAH"] = Field(
        default="UAH", title="Валюта", json_schema_extra={"readOnly": True}
    )
    locales: tuple[Literal["uk"], Literal["ru"]] = Field(
        default=("uk", "ru"), title="Языки", json_schema_extra={"readOnly": True}
    )

    @field_validator("locales", mode="before")
    @classmethod
    def fixed_locales(cls, value: object) -> tuple[str, str]:
        """Принимает оба порядка, отклоняя неполный набор и дубли."""
        if (
            not isinstance(value, (list, tuple))
            or len(value) != 2
            or not all(isinstance(item, str) for item in value)
            or set(value) != {"uk", "ru"}
        ):
            raise ValueError("Both uk and ru are required")
        return ("uk", "ru")


class RozetkaConfig(StrictModel):
    """Конфигурация API Rozetka."""

    version: Literal[1] = 1
    endpoint: Literal["https://api-seller.rozetka.com.ua"] = (
        "https://api-seller.rozetka.com.ua"
    )
    settings: RozetkaSettings = Field(default_factory=RozetkaSettings)


class RozetkaCredentials(StrictModel):
    """Постоянный API-токен хранится только зашифрованным."""

    token: SecretStr = Field(min_length=1, max_length=4096, title="API-токен")


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

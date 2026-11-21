from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

from src.modules.channels.infrastructure.platforms.base import StrictModel


class RozetkaSettings(StrictModel):
    """Фиксированные валюта и порядок языков контента магазина."""

    currency: Literal["UAH"] = Field(default="UAH", title="Валюта")
    locales: tuple[Literal["ru"], Literal["uk"]] = Field(
        default=("ru", "uk"),
        title="Языки контента",
        description="Русский — основной, Українська — дополнительный.",
        json_schema_extra={"readOnly": True},
    )

    @field_validator("locales", mode="before")
    @classmethod
    def normalize_locales(cls, value: object) -> tuple[str, str]:
        """Принимает только оба языка без дублей и фиксирует основной RU."""
        if (
            not isinstance(value, (list, tuple))
            or len(value) != 2
            or not all(isinstance(item, str) for item in value)
            or set(value) != {"ru", "uk"}
        ):
            raise ValueError("Both ru and uk are required")
        return ("ru", "uk")


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

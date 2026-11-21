from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

from src.modules.channels.infrastructure.platforms.base import StrictModel


class PromSettings(StrictModel):
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

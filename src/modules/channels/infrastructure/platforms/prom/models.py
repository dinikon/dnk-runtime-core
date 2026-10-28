from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

from src.modules.channels.infrastructure.platforms.base import StrictModel


class PromSettings(StrictModel):
    """Фиксированная валюта и две обязательные языковые версии."""

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

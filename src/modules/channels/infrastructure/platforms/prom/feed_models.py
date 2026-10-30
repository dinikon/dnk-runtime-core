from typing import Literal

from src.modules.channels.infrastructure.platforms.base import StrictModel


class PromFeedSettings(StrictModel):
    """Первый профиль: name/description на русском, отдельные украинские теги."""

    base_locale: Literal["ru"] = "ru"

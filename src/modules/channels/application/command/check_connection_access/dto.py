"""Безопасный результат проверки доступа для последующего применения."""

from dataclasses import dataclass

from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)


@dataclass(frozen=True, slots=True)
class CheckConnectionAccessResultDTO:
    """Содержит подтверждённый магазин либо код окончательного отказа."""

    identity: ResourceIdentityVO | None
    error_code: str | None

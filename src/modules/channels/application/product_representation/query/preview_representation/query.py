from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
)


@dataclass(frozen=True, slots=True)
class PreviewRepresentationQuery:
    """Запрашивает текущее представление существующей группы без записи и отправки."""

    channel_id: UUID
    group_id: UUID
    locales: tuple[str, ...] | None = None
    overrides: RepresentationOverridesVO | None = None
    expected_revision: int | None = None
    expected_binding_revision: int | None = None
    expected_config_revision: int | None = None

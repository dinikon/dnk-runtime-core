from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChannelKindListItemDTO:
    """Описывает доступность платформы в каталоге выбора."""

    kind: str
    type: str
    label: str
    can_configure: bool
    unavailable_reason: str | None

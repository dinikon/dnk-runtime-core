from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourcePathItemDTO:
    """Описывает разрешённый типизированный источник и его совместимость."""

    provider: str
    path: str
    label: str
    field_kinds: tuple[str, ...]
    requires_locale: bool


@dataclass(frozen=True, slots=True)
class ListSourcePathsResultDTO:
    """Передаёт закрытый реестр доступных прямых источников."""

    items: tuple[SourcePathItemDTO, ...]

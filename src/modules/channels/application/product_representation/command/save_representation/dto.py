from dataclasses import dataclass
from src.modules.channels.application.product_representation.contracts import (
    RepresentationState,
    RepresentationBindingItem,
)


@dataclass(frozen=True, slots=True)
class SaveRepresentationResultDTO:
    """Публичный результат сценария save_representation."""

    state: RepresentationState
    binding_revision: int
    config_revision: int
    locales: tuple[str, ...]
    items: tuple[RepresentationBindingItem, ...]

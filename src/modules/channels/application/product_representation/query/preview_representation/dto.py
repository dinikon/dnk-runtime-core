from dataclasses import dataclass

from src.modules.channels.application.product_representation.contracts import (
    PreparedRepresentation,
    RepresentationState,
)


@dataclass(frozen=True, slots=True)
class PreviewRepresentationResultDTO:
    """Результат preview; не является сохранённым ProductRepresentation."""

    representation: PreparedRepresentation
    state: RepresentationState = RepresentationState()
    export_blockers: tuple[str, ...] = ()
    draft: bool = False

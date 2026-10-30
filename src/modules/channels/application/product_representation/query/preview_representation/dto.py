from dataclasses import dataclass

from src.modules.channels.application.product_representation.contracts import (
    PreparedRepresentation,
)


@dataclass(frozen=True, slots=True)
class PreviewRepresentationResultDTO:
    """Результат preview; не является сохранённым ProductRepresentation."""

    representation: PreparedRepresentation

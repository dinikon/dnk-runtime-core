from typing import Protocol
from src.modules.contact_points.domain.contact_point.value_object.value import (
    NormalizationContext,
    NormalizedContactPoint,
)


class ContactPointNormalizerProtocol(Protocol):
    """Порт синтаксической проверки и нормализации адреса."""

    def normalize(
        self, value: str, context: NormalizationContext
    ) -> NormalizedContactPoint: ...


__all__ = ["ContactPointNormalizerProtocol"]

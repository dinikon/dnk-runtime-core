from __future__ import annotations
from enum import StrEnum


class RateDerivation(StrEnum):
    """Identity, direct, inverse or common-date cross derivation of a quote."""

    DIRECT = "direct"
    INVERSE = "inverse"
    CROSS = "cross"
    IDENTITY = "identity"


__all__ = ["RateDerivation"]

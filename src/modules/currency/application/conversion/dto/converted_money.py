from __future__ import annotations
from dataclasses import dataclass
from src.modules.currency.application.conversion.dto.conversion_snapshot import (
    ConversionSnapshot,
)
from src.modules.shared.domain.value_object.money import Money


@dataclass(frozen=True, slots=True)
class ConvertedMoney:
    """Original amount, converted amount and their reproducible conversion provenance."""

    original: Money
    converted: Money
    conversion: ConversionSnapshot


__all__ = ["ConvertedMoney"]

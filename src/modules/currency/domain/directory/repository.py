from __future__ import annotations
from typing import Protocol
from typing import Sequence
from src.modules.currency.domain.directory.entity import CurrencyInfo
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


class CurrencyDirectory(Protocol):
    """Explicit persistence contract for currency directory."""

    async def get(self, code: CurrencyCodeVO) -> CurrencyInfo: ...
    async def exists(self, code: CurrencyCodeVO) -> bool: ...
    async def list_active(self) -> Sequence[CurrencyInfo]: ...


__all__ = ["CurrencyDirectory"]

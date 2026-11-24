from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CatalogCalculationReference:
    """Выбирает SIMPLE либо конкретный VARIANT в пределах родительской карточки."""

    item_id: UUID
    variant_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CatalogCalculationSnapshot:
    """Публичная проекция цен без ORM, чужих агрегатов и валютной арифметики."""

    reference: CatalogCalculationReference
    selected_id: UUID
    kind: str
    sku: str | None
    regular: Decimal | None
    sale: Decimal | None
    effective: Decimal | None
    revision: int
    as_of: datetime
    valid_until: datetime | None
    purchase: Decimal | None = None
    category_ids: tuple[UUID, ...] = ()
    stock_quantity: int | None = None
    in_stock: bool | None = None


class CatalogCalculationItemNotFoundError(Exception):
    """Не раскрывает отсутствующую или не принадлежащую родителю позицию."""


class CatalogCalculationRequestError(Exception):
    """Отклоняет некорректный запрос публичного чтения Catalog."""


class CatalogCalculationReaderProtocol(Protocol):
    """Читает пакет выбранных продаваемых позиций на одном моменте времени."""

    async def read_many(
        self, references: tuple[CatalogCalculationReference, ...], as_of: datetime
    ) -> tuple[CatalogCalculationSnapshot, ...]:
        """Возвращает согласованные цены и реальные revision выбранных записей."""
        ...


@dataclass(frozen=True, slots=True)
class CatalogPublicationValues:
    """Передаёт цены позиции и эффективные значения полей в нужных локалях."""

    calculation: CatalogCalculationSnapshot
    texts: tuple[tuple[str, str, str | None], ...]


class CatalogPublicationValuesReaderProtocol(Protocol):
    """Читает существующие продаваемые позиции для табличного экспорта."""

    async def read_publication_values(
        self,
        references: tuple[CatalogCalculationReference, ...],
        as_of: datetime,
        locales: frozenset[str],
        content_codes: frozenset[str],
    ) -> tuple[CatalogPublicationValues, ...]:
        """Возвращает доступные позиции со значениями и опускает недоступные ссылки."""
        ...

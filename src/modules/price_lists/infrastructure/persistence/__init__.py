"""Регистрация статических tenant-моделей для Alembic и metadata."""

from src.modules.price_lists.infrastructure.persistence.offer_money.model import (
    OfferMoneySnapshotModel,
)

from src.modules.price_lists.infrastructure.persistence.models import (
    PriceListModel,
    PartnerOfferModel,
    PartnerOfferStateModel,
    PriceListSyncRunModel,
    PriceListSyncItemModel,
)

__all__ = [
    "OfferMoneySnapshotModel",
    "PriceListModel",
    "PartnerOfferModel",
    "PartnerOfferStateModel",
    "PriceListSyncRunModel",
    "PriceListSyncItemModel",
]

from src.modules.price_lists.application.offer.dto.offer_conversion_dto import (
    OfferConversionDTO,
)
from src.modules.price_lists.infrastructure.persistence.offer_money.mapper import (
    conversion_payload,
    read_conversion,
)
from datetime import date
import sqlalchemy as sa
from src.modules.shared.infrastructure.persistence import (
    TenantBase,
    StringUUID,
    PortableJSON,
)
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS
from src.modules.price_lists.infrastructure.persistence.base import SessionRepository
from src.modules.price_lists.infrastructure.persistence.models import PartnerOfferModel


class OfferMoneySnapshotModel(TenantBase):
    __table__ = sa.Table(
        "partner_offer_money_snapshots",
        TenantBase.metadata,
        sa.Column(
            "state_id",
            StringUUID,
            sa.ForeignKey(
                f"{TENANT_SCHEMA_ALIAS}.partner_offer_states.id", ondelete="CASCADE"
            ),
            primary_key=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("business_date", sa.Date),
        sa.Column("purchase_price", PortableJSON),
        sa.Column("rrp", PortableJSON),
        sa.Column("error_code", sa.String(64)),
        sa.CheckConstraint(
            "status IN ('converted','unavailable')", name="ck_offer_money_status"
        ),
        sa.CheckConstraint(
            "(status = 'converted' AND error_code IS NULL AND business_date IS NOT NULL) OR (status = 'unavailable' AND error_code IS NOT NULL)",
            name="ck_offer_money_result",
        ),
    )


__all__ = ["OfferMoneySnapshotModel"]

from datetime import date
import sqlalchemy as sa

from src.modules.shared.infrastructure.persistence import (
    TenantBase,
    StringUUID,
    PortableJSON,
)
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS
from .base import SessionRepository
from .models import PartnerOfferModel


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


class SqlOfferMoneyRepository(SessionRepository):
    async def add_many(self, *, tenant_id, records):
        values = [
            {
                **record,
                "business_date": (
                    date.fromisoformat(record["business_date"])
                    if record["business_date"]
                    else None
                ),
            }
            for record in records
        ]
        await self.insert_many(tenant_id, OfferMoneySnapshotModel.__table__, values)

    async def read_many(self, *, tenant_id, ids, history):
        if not ids:
            return {}
        table = OfferMoneySnapshotModel.__table__
        if history:
            query = sa.select(table, table.c.state_id.label("item_id")).where(
                table.c.state_id.in_(ids)
            )
        else:
            offers = PartnerOfferModel.__table__
            query = (
                sa.select(table, offers.c.id.label("item_id"))
                .join(offers, offers.c.current_state_id == table.c.state_id)
                .where(offers.c.id.in_(ids))
            )
        rows = (
            await self.session.execute(
                query.execution_options(**self.execution_options(tenant_id))
            )
        ).mappings()
        return {
            row["item_id"]: {
                "status": row["status"],
                "business_date": (
                    row["business_date"].isoformat() if row["business_date"] else None
                ),
                "purchase_price": row["purchase_price"],
                "rrp": row["rrp"],
                "error_code": row["error_code"],
            }
            for row in rows
        }

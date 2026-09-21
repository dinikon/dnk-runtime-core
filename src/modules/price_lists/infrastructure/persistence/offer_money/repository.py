from src.modules.price_lists.infrastructure.persistence.offer_money.model import (
    OfferMoneySnapshotModel,
)
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


class SqlOfferMoneyRepository(SessionRepository):
    async def add_many(self, *, tenant_id, records):
        values = [
            dict(
                state_id=r.state_id.uuid,
                status=r.conversion.status,
                business_date=r.conversion.business_date,
                purchase_price=conversion_payload(r.conversion.purchase_price),
                rrp=conversion_payload(r.conversion.rrp),
                error_code=r.conversion.error_code,
            )
            for r in records
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
            row["item_id"]: OfferConversionDTO(
                row["status"],
                row["business_date"],
                read_conversion(row["purchase_price"]),
                read_conversion(row["rrp"]),
                row["error_code"],
            )
            for row in rows
        }


__all__ = ["SqlOfferMoneyRepository"]

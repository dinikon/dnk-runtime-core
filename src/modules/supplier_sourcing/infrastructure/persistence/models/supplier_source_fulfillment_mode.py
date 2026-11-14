from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class SupplierSourceFulfillmentModeModel(TenantBase):
    """Хранит набор значений, принадлежащий агрегату источника."""

    __tablename__ = "supplier_source_fulfillment_modes"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "supplier_source_id", "mode", name="pk_supplier_source_fulfillment_modes"
        ),
        sa.ForeignKeyConstraint(
            ["supplier_source_id"],
            ["tenant.supplier_sources.id"],
            name="fk_supplier_source_modes_source",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "mode IN ('DROPSHIP', 'PURCHASE_TO_WAREHOUSE')",
            name="ck_supplier_source_modes_mode",
        ),
    )
    supplier_source_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    mode: Mapped[str] = mapped_column(sa.Text(), nullable=False)

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ItemBarcodeModel(TenantBase):
    """Хранит дочерние штрихкоды с уникальностью во всей tenant-схеме."""

    __tablename__ = "inventory_item_barcodes"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_inventory_item_barcodes"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["tenant.inventory_items.id"],
            name="fk_inventory_item_barcodes_item",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("barcode", name="uq_inventory_item_barcodes_barcode"),
        sa.UniqueConstraint(
            "inventory_item_id", "position", name="uq_inventory_item_barcodes_position"
        ),
        sa.CheckConstraint(
            "char_length(barcode) > 0", name="ck_inventory_item_barcodes_barcode"
        ),
        sa.CheckConstraint("position >= 0", name="ck_inventory_item_barcodes_position"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    barcode: Mapped[str] = mapped_column(sa.Text(collation="C"), nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)

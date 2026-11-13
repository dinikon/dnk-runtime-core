from decimal import Decimal
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ItemPackagingModel(TenantBase):
    """Хранит вариант упаковки как дочернюю часть агрегата InventoryItem."""

    __tablename__ = "inventory_item_packagings"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_inventory_item_packagings"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["tenant.inventory_items.id"],
            name="fk_item_packagings_item",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["packaging_type_id"],
            ["tenant.packaging_types.id"],
            name="fk_item_packagings_type",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "inventory_item_id", "code", name="uq_item_packagings_code"
        ),
        sa.UniqueConstraint(
            "inventory_item_id", "position", name="uq_item_packagings_position"
        ),
        sa.CheckConstraint(
            "char_length(btrim(code)) > 0", name="ck_item_packagings_code"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_item_packagings_name"
        ),
        sa.CheckConstraint(
            "char_length(btrim(content_uom)) > 0", name="ck_item_packagings_uom"
        ),
        sa.CheckConstraint(
            "content_quantity > 0 AND content_quantity < 'Infinity'::numeric",
            name="ck_item_packagings_quantity",
        ),
        sa.CheckConstraint("position >= 0", name="ck_item_packagings_position"),
        sa.Index("ix_item_packagings_type", "packaging_type_id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    packaging_type_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    code: Mapped[str] = mapped_column(sa.Text(collation="C"), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    content_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(), nullable=False)
    content_uom: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer(), nullable=False)

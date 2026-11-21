from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockLocationModel(TenantBase):
    """Хранит самостоятельный адрес без остатков и коллекций дочерних адресов."""

    __tablename__ = "stock_locations"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_stock_locations"),
        sa.UniqueConstraint(
            "warehouse_id", "code", name="uq_stock_locations_warehouse_code"
        ),
        sa.UniqueConstraint(
            "id", "warehouse_id", name="uq_stock_locations_id_warehouse"
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["tenant.warehouses.id"],
            name="fk_stock_locations_warehouse",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_location_id", "warehouse_id"],
            ["tenant.stock_locations.id", "tenant.stock_locations.warehouse_id"],
            name="fk_stock_locations_parent",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "parent_location_id <> id", name="ck_stock_locations_not_self_parent"
        ),
        sa.CheckConstraint(
            "char_length(btrim(code)) > 0", name="ck_stock_locations_code"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_stock_locations_name"
        ),
        sa.CheckConstraint(
            "location_type IN ('STORAGE', 'RECEIVING', 'SHIPPING', 'QUARANTINE', 'TRANSIT')",
            name="ck_stock_locations_type",
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    parent_location_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)
    code: Mapped[str] = mapped_column(sa.Text(collation="C"), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    location_type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)

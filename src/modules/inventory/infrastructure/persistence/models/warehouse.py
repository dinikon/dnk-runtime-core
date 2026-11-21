from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class WarehouseModel(TenantBase):
    """Хранит карточку склада и ссылку на основную локацию текущего tenant."""

    __tablename__ = "warehouses"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_warehouses"),
        sa.UniqueConstraint("code", name="uq_warehouses_code"),
        sa.CheckConstraint("char_length(btrim(code)) > 0", name="ck_warehouses_code"),
        sa.CheckConstraint("char_length(btrim(name)) > 0", name="ck_warehouses_name"),
        sa.ForeignKeyConstraint(
            ["default_storage_location_id", "id"],
            ["tenant.stock_locations.id", "tenant.stock_locations.warehouse_id"],
            name="fk_warehouses_default_storage_location",
            ondelete="RESTRICT",
            use_alter=True,
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    code: Mapped[str] = mapped_column(sa.Text(collation="C"), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
    default_storage_location_id: Mapped[UUID | None] = mapped_column(
        StringUUID, nullable=True
    )

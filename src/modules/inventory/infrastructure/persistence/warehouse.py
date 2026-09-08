from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase
from src.modules.shared.infrastructure.persistence.tenant_system_mixin import (
    TenantSystemMixin,
)
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS


class WarehouseModel(TenantSystemMixin, TenantBase):
    """Статическая tenant-модель склада; структура управляется Alembic."""

    __tablename__ = "warehouses"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_warehouses"),
        CheckConstraint("parent_id <> id", name="ck_warehouses_parent_not_self"),
        Index("ix_warehouses_parent_id", "parent_id"),
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        ForeignKey(
            f"{TENANT_SCHEMA_ALIAS}.warehouses.id",
            name="fk_warehouses_parent_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

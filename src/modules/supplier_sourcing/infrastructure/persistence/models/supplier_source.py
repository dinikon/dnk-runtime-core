from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class SupplierSourceModel(TenantBase):
    """Хранит настройки внешнего источника в tenant-схеме."""

    __tablename__ = "supplier_sources"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_supplier_sources"),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_supplier_sources_name"
        ),
        sa.CheckConstraint(
            "external_warehouse_code IS NULL OR char_length(btrim(external_warehouse_code)) > 0",
            name="ck_supplier_sources_external_code",
        ),
        sa.CheckConstraint(
            "default_lead_time_seconds >= 0 AND default_lead_time_seconds <= 86399999999999",
            name="ck_supplier_sources_lead_time",
        ),
        sa.CheckConstraint(
            "stock_ttl_seconds > 0 AND stock_ttl_seconds <= 86399999999999",
            name="ck_supplier_sources_ttl",
        ),
        sa.CheckConstraint(
            "stale_behavior IN ('MARK_UNKNOWN', 'BLOCK_AUTOMATIC_SALE')",
            name="ck_supplier_sources_stale",
        ),
        sa.CheckConstraint(
            "missing_sku_behavior IN ('KEEP_LAST', 'MARK_UNKNOWN')",
            name="ck_supplier_sources_missing",
        ),
        sa.CheckConstraint(
            "supplier_model_key IN ('crm.company', 'crm.contact')",
            name="ck_supplier_sources_supplier_model_key",
        ),
        sa.Index("ix_supplier_sources_supplier", "supplier_model_key", "supplier_id"),
        sa.Index("ix_supplier_sources_name_id", "name", "id"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    supplier_model_key: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    external_warehouse_code: Mapped[str | None] = mapped_column(
        sa.Text(collation="C"), nullable=True
    )
    default_lead_time_seconds: Mapped[int] = mapped_column(
        sa.BigInteger(), nullable=False
    )
    stock_ttl_seconds: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    stale_behavior: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    missing_sku_behavior: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)

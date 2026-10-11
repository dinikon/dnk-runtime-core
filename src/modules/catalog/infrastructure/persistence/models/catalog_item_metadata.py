from uuid import UUID
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemMetadataModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item_metadata"
    __table_args__ = (
        sa.CheckConstraint(
            "decimal_value IS NULL OR (decimal_value NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(decimal_value)<=6)",
            name="ck_catalog_metadata_decimal_precision",
        ),
        sa.UniqueConstraint(
            "catalog_item_id", "position", name="uq_catalog_item_metadata_position"
        ),
        sa.CheckConstraint(
            "position>=0 AND ((mode='clear' AND value_type IS NULL AND text_value IS NULL AND decimal_value IS NULL AND boolean_value IS NULL) OR (mode='set' AND ((value_type='text' AND text_value IS NOT NULL AND decimal_value IS NULL AND boolean_value IS NULL) OR (value_type='decimal' AND text_value IS NULL AND decimal_value IS NOT NULL AND boolean_value IS NULL) OR (value_type='boolean' AND text_value IS NULL AND decimal_value IS NULL AND boolean_value IS NOT NULL))))",
            name="ck_catalog_item_metadata_value",
        ),
    )
    catalog_item_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    key: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    mode: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    value_type: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    text_value: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    decimal_value: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    boolean_value: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)

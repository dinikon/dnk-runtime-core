from uuid import UUID
from datetime import datetime
from decimal import Decimal
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item"
    __table_args__ = (
        sa.UniqueConstraint("id", "kind", name="uq_catalog_item_id_kind"),
        sa.UniqueConstraint("parent_id", "id", name="uq_catalog_item_parent_id"),
        sa.ForeignKeyConstraint(
            ["parent_id", "required_parent_kind"],
            ["tenant.catalog_item.id", "tenant.catalog_item.kind"],
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
            name="fk_catalog_item_parent_role",
        ),
        sa.CheckConstraint(
            "kind IN ('simple','variable','variant')", name="ck_catalog_item_kind"
        ),
        sa.CheckConstraint(
            "status IN ('draft','active','archived')", name="ck_catalog_item_status"
        ),
        sa.CheckConstraint("revision>0", name="ck_catalog_item_revision"),
        sa.CheckConstraint(
            "(kind='variant' AND parent_id IS NOT NULL AND parent_id<>id AND product_type_id IS NULL) OR (kind IN ('simple','variable') AND parent_id IS NULL AND product_type_id IS NOT NULL)",
            name="ck_catalog_item_role",
        ),
        sa.Index(
            "uq_catalog_item_sku",
            "sku",
            unique=True,
            postgresql_where=sa.text("sku IS NOT NULL"),
        ),
        sa.Index(
            "ix_catalog_item_roots",
            "created_at",
            "id",
            postgresql_where=sa.text("parent_id IS NULL"),
        ),
        sa.CheckConstraint(
            "kind<>'variable' OR (virtual=false AND regular_price IS NULL)",
            name="ck_catalog_item_variable_values",
        ),
        sa.CheckConstraint(
            "(regular_price IS NOT NULL AND regular_price>=0 AND currency IS NOT NULL AND currency ~ '^[A-Z]{3}$') OR (regular_price IS NULL AND currency IS NULL AND sale_price IS NULL AND date_on_sale_from IS NULL AND date_on_sale_to IS NULL)",
            name="ck_catalog_item_price",
        ),
        sa.CheckConstraint(
            "(sale_price IS NULL AND date_on_sale_from IS NULL AND date_on_sale_to IS NULL) OR (sale_price IS NOT NULL AND sale_price>=0 AND sale_price<=regular_price)",
            name="ck_catalog_item_sale_price",
        ),
        sa.CheckConstraint(
            "date_on_sale_from IS NULL OR date_on_sale_to IS NULL OR date_on_sale_from<=date_on_sale_to",
            name="ck_catalog_item_sale_interval",
        ),
        sa.CheckConstraint(
            "(weight IS NULL AND weight_unit IS NULL) OR (weight IS NOT NULL AND weight_unit IS NOT NULL AND weight_unit IN ('g','kg') AND weight>=0 AND weight NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND weight * (CASE WHEN weight_unit='kg' THEN 1000 ELSE 1 END) = trunc(weight * (CASE WHEN weight_unit='kg' THEN 1000 ELSE 1 END), 6))",
            name="ck_catalog_item_weight",
        ),
        sa.CheckConstraint(
            "(length IS NULL AND length_unit IS NULL) OR (length IS NOT NULL AND length_unit IS NOT NULL AND length_unit IN ('cm','m') AND length>=0 AND length NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND length * (CASE WHEN length_unit='m' THEN 1000 ELSE 10 END) = trunc(length * (CASE WHEN length_unit='m' THEN 1000 ELSE 10 END), 6))",
            name="ck_catalog_item_length",
        ),
        sa.CheckConstraint(
            "(width IS NULL AND width_unit IS NULL) OR (width IS NOT NULL AND width_unit IS NOT NULL AND width_unit IN ('cm','m') AND width>=0 AND width NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND width * (CASE WHEN width_unit='m' THEN 1000 ELSE 10 END) = trunc(width * (CASE WHEN width_unit='m' THEN 1000 ELSE 10 END), 6))",
            name="ck_catalog_item_width",
        ),
        sa.CheckConstraint(
            "(height IS NULL AND height_unit IS NULL) OR (height IS NOT NULL AND height_unit IS NOT NULL AND height_unit IN ('cm','m') AND height>=0 AND height NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND height * (CASE WHEN height_unit='m' THEN 1000 ELSE 10 END) = trunc(height * (CASE WHEN height_unit='m' THEN 1000 ELSE 10 END), 6))",
            name="ck_catalog_item_height",
        ),
        sa.CheckConstraint(
            "regular_price IS NULL OR (regular_price NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(regular_price)<=6)",
            name="ck_catalog_item_regular_price_precision",
        ),
        sa.CheckConstraint(
            "sale_price IS NULL OR (sale_price NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(sale_price)<=6)",
            name="ck_catalog_item_sale_price_precision",
        ),
        sa.CheckConstraint(
            "(manage_stock=true AND stock_quantity IS NOT NULL AND stock_status IS NULL AND backorders IN ('no','notify','yes')) OR (manage_stock=false AND stock_quantity IS NULL AND stock_status IS NOT NULL AND stock_status IN ('in_stock','out_of_stock','on_backorder') AND backorders='no')",
            name="ck_catalog_item_stock",
        ),
    )
    kind: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        StringUUID, nullable=True, index=True
    )
    required_parent_kind: Mapped[str | None] = mapped_column(
        sa.String(20),
        sa.Computed(
            "CASE WHEN kind='variant' THEN 'variable' ELSE NULL END", persisted=True
        ),
        nullable=True,
    )
    product_type_id: Mapped[UUID | None] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_product_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    sku: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    revision: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    virtual: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    weight_unit: Mapped[str | None] = mapped_column(sa.String(2), nullable=True)
    regular_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    sale_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    currency: Mapped[str | None] = mapped_column(sa.String(3), nullable=True)
    date_on_sale_from: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    date_on_sale_to: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    length: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    length_unit: Mapped[str | None] = mapped_column(sa.String(2), nullable=True)
    width: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    width_unit: Mapped[str | None] = mapped_column(sa.String(2), nullable=True)
    height: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    height_unit: Mapped[str | None] = mapped_column(sa.String(2), nullable=True)
    manage_stock: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    stock_quantity: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    stock_status: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    backorders: Mapped[str] = mapped_column(sa.String(10), nullable=False)

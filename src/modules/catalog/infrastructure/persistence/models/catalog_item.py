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
        sa.CheckConstraint(
            "kind<>'variable' OR sku IS NULL", name="ck_catalog_item_sku_role"
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
            "virtual_mode IN ('set','inherit','clear') AND (kind='variant' OR virtual_mode<>'inherit')",
            name="ck_catalog_item_virtual_mode",
        ),
        sa.CheckConstraint(
            "price_mode IN ('set','inherit','clear') AND (kind='variant' OR price_mode<>'inherit')",
            name="ck_catalog_item_price_mode",
        ),
        sa.CheckConstraint(
            "weight_mode IN ('set','inherit','clear') AND (kind='variant' OR weight_mode<>'inherit')",
            name="ck_catalog_item_weight_mode",
        ),
        sa.CheckConstraint(
            "dimensions_mode IN ('set','inherit','clear') AND (kind='variant' OR dimensions_mode<>'inherit')",
            name="ck_catalog_item_dimensions_mode",
        ),
        sa.CheckConstraint(
            "virtual_mode<>'clear' AND ((virtual_mode='set' AND virtual IS NOT NULL) OR (virtual_mode='inherit' AND virtual IS NULL))",
            name="ck_catalog_item_virtual",
        ),
        sa.CheckConstraint(
            "(weight_mode='set' AND weight>=0 AND weight IS NOT NULL) OR (weight_mode<>'set' AND weight IS NULL)",
            name="ck_catalog_item_weight",
        ),
        sa.CheckConstraint(
            "(dimensions_mode='set' AND length IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL AND length>=0 AND width>=0 AND height>=0) OR (dimensions_mode<>'set' AND length IS NULL AND width IS NULL AND height IS NULL)",
            name="ck_catalog_item_dimensions",
        ),
        sa.CheckConstraint(
            "(price_mode='set' AND regular_price IS NOT NULL AND regular_price>=0 AND currency IS NOT NULL AND currency ~ '^[A-Z]{3}$') OR (price_mode<>'set' AND regular_price IS NULL AND currency IS NULL AND sale_price IS NULL AND date_on_sale_from IS NULL AND date_on_sale_to IS NULL)",
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
            "weight IS NULL OR (weight NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(weight)<=6)",
            name="ck_catalog_item_weight_precision",
        ),
        sa.CheckConstraint(
            "length IS NULL OR (length NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(length)<=6)",
            name="ck_catalog_item_length_precision",
        ),
        sa.CheckConstraint(
            "width IS NULL OR (width NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(width)<=6)",
            name="ck_catalog_item_width_precision",
        ),
        sa.CheckConstraint(
            "height IS NULL OR (height NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric) AND scale(height)<=6)",
            name="ck_catalog_item_height_precision",
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
            "manage_stock IS NULL OR manage_stock IN ('none','own','parent')",
            name="ck_catalog_item_stock_mode",
        ),
        sa.CheckConstraint(
            "(manage_stock IS NULL AND stock_quantity IS NULL AND stock_status IS NULL AND backorders IS NULL) OR (manage_stock='parent' AND kind='variant' AND stock_quantity IS NULL AND stock_status IS NULL AND backorders IS NULL) OR (manage_stock='own' AND stock_quantity IS NOT NULL AND stock_quantity>=0 AND stock_status IS NULL AND backorders IS NOT NULL AND backorders IN ('no','notify','yes')) OR (manage_stock='none' AND stock_quantity IS NULL AND stock_status IS NOT NULL AND backorders IS NOT NULL AND stock_status IN ('in_stock','out_of_stock','on_backorder') AND backorders IN ('no','notify','yes') AND (stock_status<>'on_backorder' OR backorders<>'no'))",
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
    virtual_mode: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    virtual: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    weight_mode: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    price_mode: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    regular_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    sale_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    currency: Mapped[str | None] = mapped_column(sa.String(3), nullable=True)
    date_on_sale_from: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    date_on_sale_to: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    dimensions_mode: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    length: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    width: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    height: Mapped[Decimal | None] = mapped_column(sa.Numeric(), nullable=True)
    manage_stock: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    stock_quantity: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    stock_status: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    backorders: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)

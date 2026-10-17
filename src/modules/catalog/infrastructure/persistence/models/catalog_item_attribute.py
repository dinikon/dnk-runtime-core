from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemAttributeModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item_attributes"
    __table_args__ = (
        sa.CheckConstraint(
            "mode IN ('set','clear') AND (NOT is_variation OR mode='set') AND position>=0",
            name="ck_catalog_item_attribute",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "required_kind"],
            ["tenant.catalog_item.id", "tenant.catalog_item.kind"],
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.UniqueConstraint(
            "catalog_item_id",
            "attribute_id",
            "is_variation",
            name="uq_catalog_attribute_role",
        ),
        sa.UniqueConstraint(
            "catalog_item_id",
            "is_variation",
            "position",
            name="uq_catalog_attribute_position",
        ),
    )
    catalog_item_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attribute_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_attributes.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    mode: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    visible: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    is_variation: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    required_kind: Mapped[str | None] = mapped_column(
        sa.String(20),
        sa.Computed(
            "CASE WHEN is_variation THEN 'variable' ELSE NULL END", persisted=True
        ),
        nullable=True,
    )

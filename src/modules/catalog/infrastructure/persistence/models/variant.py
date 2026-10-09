from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class VariantModel(TenantBase):
    """Позиция SIMPLE; уникальный product_id фиксирует максимум одну позицию."""

    __tablename__ = "catalog_variants"
    __table_args__ = (
        sa.CheckConstraint(
            "downloadable=false", name="ck_catalog_variant_files_unavailable"
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    product_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    virtual: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    downloadable: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

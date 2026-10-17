from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemGalleryModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item_galleries"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "locale", "primary_image_id"],
            [
                "tenant.catalog_item_images.catalog_item_id",
                "tenant.catalog_item_images.locale",
                "tenant.catalog_item_images.id",
            ],
            name="fk_catalog_gallery_primary",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
    )
    catalog_item_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    locale: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    primary_image_id: Mapped[UUID | None] = mapped_column(StringUUID, nullable=True)

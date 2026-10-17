from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemContentValueModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item_content_values"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "locale"],
            [
                "tenant.catalog_item_translations.catalog_item_id",
                "tenant.catalog_item_translations.locale",
            ],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "(mode='set' AND value IS NOT NULL) OR (mode='clear' AND value IS NULL)",
            name="ck_catalog_item_content_mode",
        ),
    )
    catalog_item_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    locale: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    block_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.catalog_content_block_definitions.id", ondelete="RESTRICT"
        ),
        primary_key=True,
    )
    mode: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    value: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

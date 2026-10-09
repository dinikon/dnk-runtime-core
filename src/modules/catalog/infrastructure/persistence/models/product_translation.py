from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductTranslationModel(TenantBase):
    """Наличие перевода контента для явной locale без fallback."""

    __tablename__ = "catalog_product_translations"
    product_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    locale: Mapped[str] = mapped_column(sa.String(64), primary_key=True)

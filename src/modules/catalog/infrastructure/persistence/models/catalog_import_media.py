from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogImportMediaModel(TenantBase):
    """Снимок загрузки URL для безопасного повтора в пределах одного импорта."""

    __tablename__ = "catalog_import_media"
    __table_args__ = (
        sa.UniqueConstraint(
            "import_id", "url_hash", name="uq_catalog_import_media_url"
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True)
    import_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("tenant.catalog_imports.id", ondelete="CASCADE")
    )
    url_hash: Mapped[str] = mapped_column(sa.String(64))
    file_id: Mapped[UUID | None] = mapped_column(sa.Uuid)
    error: Mapped[str | None] = mapped_column(sa.String(500))

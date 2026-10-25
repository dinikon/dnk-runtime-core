from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogImportRowModel(TenantBase):
    """Исходная запись и единственный результат её обработки."""

    __tablename__ = "catalog_import_rows"
    __table_args__ = (
        sa.UniqueConstraint("import_id", "number", name="uq_catalog_import_row_number"),
        sa.CheckConstraint(
            "number>0 AND outcome IN ('pending','created','updated','skipped','errors')",
            name="ck_catalog_import_row",
        ),
        sa.Index("ix_catalog_import_row_pending", "import_id", "outcome", "number"),
        sa.Index("ix_catalog_import_row_sku", "import_id", "sku", "number"),
    )
    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True)
    import_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("tenant.catalog_imports.id", ondelete="CASCADE")
    )
    number: Mapped[int] = mapped_column(sa.Integer)
    values: Mapped[dict[str, list[str]]] = mapped_column(JSONB)
    outcome: Mapped[str] = mapped_column(sa.String(16), default="pending")
    sku: Mapped[str | None] = mapped_column(sa.String(255))
    item_id: Mapped[UUID | None] = mapped_column(sa.Uuid)
    errors: Mapped[list[str]] = mapped_column(JSONB, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)

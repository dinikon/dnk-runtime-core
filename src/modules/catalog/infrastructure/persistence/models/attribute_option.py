from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class AttributeOptionModel(TenantBase):
    """Внутренний option определения с устойчивым ID и кодом."""

    __tablename__ = "catalog_attribute_options"
    __table_args__ = (
        sa.UniqueConstraint("attribute_id", "id", name="uq_catalog_option_owner"),
        sa.UniqueConstraint("attribute_id", "code", name="uq_catalog_option_code"),
        sa.UniqueConstraint(
            "attribute_id",
            "position",
            name="uq_catalog_option_position",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint("position>=0", name="ck_catalog_option_position"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    attribute_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_attributes.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)

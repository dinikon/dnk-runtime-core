from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class AttributeTranslationModel(TenantBase):
    """Независимая подпись одной явной locale."""

    __tablename__ = "catalog_attribute_translations"
    __table_args__ = (
        sa.CheckConstraint(
            "char_length(btrim(label)) BETWEEN 1 AND 255",
            name="ck_attribute_translation_label",
        ),
    )
    attribute_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_attributes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    locale: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    label: Mapped[str] = mapped_column(sa.String(255), nullable=False)

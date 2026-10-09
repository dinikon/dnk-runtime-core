from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class VariantContentValueModel(TenantBase):
    """Строковое значение блока одного перевода; связь и locale явны в колонках."""

    __tablename__ = "catalog_variant_content_values"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["variant_id", "locale"],
            [
                "tenant.catalog_variant_translations.variant_id",
                "tenant.catalog_variant_translations.locale",
            ],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(value)<=100000", name="ck_variant_content_value_length"
        ),
    )
    variant_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    locale: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    block_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey(
            "tenant.catalog_content_block_definitions.id", ondelete="RESTRICT"
        ),
        primary_key=True,
    )
    value: Mapped[str] = mapped_column(sa.Text(), nullable=False)

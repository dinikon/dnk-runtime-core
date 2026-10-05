from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class OptionContentModel(TenantBase):
    __tablename__ = "catalog_option_contents"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "option_id", "locale_code", name="pk_catalog_option_contents"
        ),
        sa.ForeignKeyConstraint(
            ["option_id"],
            ["tenant.catalog_attribute_options.id"],
            name="fk_catalog_option_contents_option",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_option_contents_name",
        ),
    )

    option_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    locale_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)

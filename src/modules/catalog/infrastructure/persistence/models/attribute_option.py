from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class AttributeOptionModel(TenantBase):
    __tablename__ = "catalog_attribute_options"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_attribute_options"),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["tenant.catalog_attributes.id"],
            name="fk_catalog_attribute_options_attribute",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "attribute_id", "code", name="uq_catalog_attribute_options_code"
        ),
        sa.UniqueConstraint(
            "id", "attribute_id", name="uq_catalog_attribute_options_id_attribute"
        ),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    attribute_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    code: Mapped[str] = mapped_column(sa.String(64), nullable=False)

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductTypeModel(TenantBase):
    __tablename__ = "catalog_product_types"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_product_types"),
        sa.UniqueConstraint("code", name="uq_catalog_product_types_code"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    code: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    schema_version: Mapped[int] = mapped_column(sa.Integer, nullable=False)

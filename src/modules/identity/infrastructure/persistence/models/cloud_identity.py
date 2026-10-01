from datetime import datetime
from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import (
    TENANT_SCHEMA_ALIAS,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CloudIdentityModel(TenantBase):
    __tablename__ = "cloud_identities"
    __table_args__ = (
        sa.UniqueConstraint("issuer", "subject", name="uq_cloud_identity_subject"),
    )
    user_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey(f"{TENANT_SCHEMA_ALIAS}.users.id"), primary_key=True
    )
    issuer: Mapped[str] = mapped_column(sa.String(2048), nullable=False)
    subject: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

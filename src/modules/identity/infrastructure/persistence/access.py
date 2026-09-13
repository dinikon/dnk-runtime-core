"""Tenant-local invitation and cloud identity records."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence import StringUUID
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS
from src.modules.shared.infrastructure.persistence.tenant_base import TenantBase


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


class InvitationModel(TenantBase):
    __tablename__ = "invitations"
    __table_args__ = (
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_invitations_role"),
        sa.CheckConstraint(
            "state IN ('pending', 'accepted', 'revoked')", name="ck_invitations_state"
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey(f"{TENANT_SCHEMA_ALIAS}.users.id"), nullable=False
    )
    accepted_by: Mapped[UUID | None] = mapped_column(
        StringUUID, sa.ForeignKey(f"{TENANT_SCHEMA_ALIAS}.users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

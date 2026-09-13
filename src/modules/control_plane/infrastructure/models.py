"""Global integration records. No installation or access history is TTL deleted."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence import Base, PortableJSON, StringUUID


class InstallationModel(Base):
    __tablename__ = "cp_installations"
    core_tenant_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    runtime_tenant_id: Mapped[UUID] = mapped_column(
        StringUUID, unique=True, nullable=False
    )
    hostname: Mapped[str] = mapped_column(String(253), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_attempt_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    owner_user_id: Mapped[UUID | None] = mapped_column(StringUUID)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ProvisioningAttemptModel(Base):
    __tablename__ = "cp_provisioning_attempts"
    __table_args__ = (
        CheckConstraint("state IN ('queued','running','succeeded','failed')"),
        CheckConstraint("resources_state IN ('absent','present','unknown')"),
        Index("cp_attempt_recovery_idx", "state", "lease_until", "next_attempt_at"),
    )
    attempt_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    operation_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    core_tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    command_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_command: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    resources_state: Mapped[str] = mapped_column(String(16), nullable=False)
    step: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")
    step_duration_ms: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    fencing_token: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CloudConnectionModel(Base):
    __tablename__ = "cp_cloud_connections"
    runtime_tenant_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    core_tenant_id: Mapped[UUID] = mapped_column(
        StringUUID, unique=True, nullable=False
    )
    issuer: Mapped[str] = mapped_column(String(2048), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    callback: Mapped[str] = mapped_column(String(2048), nullable=False)
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)


class AccessProjectionModel(Base):
    __tablename__ = "cp_access_projections"
    __table_args__ = (CheckConstraint("version >= 1"),)
    core_tenant_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    global_user_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)


class DeliveryModel(Base):
    """Immutable event identity/payload; retry and claim state are separate."""

    __tablename__ = "cp_delivery_outbox"
    __table_args__ = (
        CheckConstraint("kind IN ('install','access')"),
        CheckConstraint("state IN ('pending','running','delivered','blocked')"),
        Index("cp_delivery_due_idx", "state", "next_attempt_at", "lease_until"),
        UniqueConstraint(
            "kind",
            "core_tenant_id",
            "aggregate_id",
            "version",
            name="cp_delivery_version_uq",
        ),
    )
    event_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    core_tenant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    fencing_token: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReadinessObservationModel(Base):
    __tablename__ = "cp_readiness_observations"
    key: Mapped[str] = mapped_column(String(253), primary_key=True)
    routing_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tls_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

from datetime import datetime
from uuid import UUID

import uuid6
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.db import Base, StringUUID


class ObjectORM(Base):
    __tablename__ = "objects"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
        default=uuid6.uuid7,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    tenant_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    data_source_id: Mapped[UUID] = mapped_column(
        StringUUID,
        ForeignKey("data_sources.id"),
        nullable=False,
        index=True,
    )

    object_type: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default="object"
    )
    singular_name: Mapped[str] = mapped_column(String(255), nullable=False)
    plural_name: Mapped[str] = mapped_column(String(255), nullable=False)

    singular_label: Mapped[str] = mapped_column(String(255), nullable=False)
    plural_label: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "plural_name", name="uq_objects_tenant_plural_name"
        ),
    )

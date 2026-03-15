from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, func, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from modules.shared.db import StringUUID
from src.modules.shared.db import Base


class SchemaORM(Base):
    __tablename__ = "schemas"

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey(column="tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
    type: Mapped[str] = mapped_column(String, nullable=False)
    schema_name: Mapped[str] = mapped_column(String, nullable=False)

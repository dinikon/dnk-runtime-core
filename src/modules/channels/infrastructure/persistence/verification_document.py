"""Формат JSON-документа проверки в SQL-хранилище."""

from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from src.modules.channels.domain.enum.verification_status import VerificationStatus


class VerificationDocument(BaseModel):
    """Версионируемая SQL-форма текущей проверки."""

    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    job_id: UUID
    config_revision: int = Field(gt=0)
    status: VerificationStatus
    checked_at: datetime | None
    error_code: str | None

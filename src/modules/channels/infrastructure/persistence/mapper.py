from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.channels.application.port.query_repository import (
    ChannelReadRow,
    ConnectionConfigReadRow,
    ResourceIdentityReadRow,
    VerificationReadRow,
)
from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.connection import Connection
from src.modules.channels.domain.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.value_object.channel_name import ChannelNameVO
from src.modules.channels.domain.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.domain.value_object.verification import VerificationVO
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class VerificationDocument(BaseModel):
    """Версионируемая SQL-форма текущей проверки."""

    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    job_id: UUID
    config_revision: int = Field(gt=0)
    status: VerificationStatus
    checked_at: datetime | None
    error_code: str | None


def read_verification(row: ConnectionModel) -> VerificationVO:
    """Восстанавливает строго типизированный документ SQL."""
    record = VerificationDocument.model_validate(row.verification)
    return VerificationVO(
        job_id=EntityIdVO.from_value(record.job_id),
        config_revision=record.config_revision,
        status=record.status,
        checked_at=record.checked_at,
        error_code=record.error_code,
    )


def write_verification(value: VerificationVO) -> JsonObject:
    """Сериализует только безопасные поля результата."""
    return VerificationDocument(
        job_id=value.job_id.uuid,
        config_revision=value.config_revision,
        status=value.status,
        checked_at=value.checked_at,
        error_code=value.error_code,
    ).model_dump(mode="json")


def read_identity(row: ConnectionModel) -> ResourceIdentityVO | None:
    """Читает нормализованную identity из индексируемых колонок."""
    return (
        ResourceIdentityVO(namespace=row.identity_namespace, key=row.identity_key)
        if row.identity_namespace is not None or row.identity_key is not None
        else None
    )


def to_domain(row: ChannelModel, c: ConnectionModel) -> Channel:
    """Восстанавливает Entity и Aggregate через явные фабрики."""
    connection = Connection.restore(
        connection_id=EntityIdVO.from_value(c.id),
        config=ConnectionConfigVO.create(
            version=c.config_version,
            endpoint=c.endpoint,
            settings=c.settings,
        ),
        encrypted_credentials=c.encrypted_credentials,
        config_revision=c.config_revision,
        identity=read_identity(c),
        verification=read_verification(c),
    )
    return Channel.restore(
        channel_id=EntityIdVO.from_value(row.id),
        name=ChannelNameVO(row.name),
        platform_kind=row.platform_kind,
        revision=row.revision,
        connection=connection,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=EntityIdVO.from_value(row.created_by),
        updated_by=EntityIdVO.from_value(row.updated_by),
    )


def to_read_row(row: ChannelModel, c: ConnectionModel) -> ChannelReadRow:
    """Читает публичные примитивы без восстановления и сериализации Domain VO."""
    verification = VerificationDocument.model_validate(c.verification)
    identity = (
        ResourceIdentityReadRow(namespace=c.identity_namespace, key=c.identity_key)
        if c.identity_namespace is not None and c.identity_key is not None
        else None
    )
    return ChannelReadRow(
        id=row.id,
        name=row.name,
        platform_kind=row.platform_kind,
        revision=row.revision,
        config=ConnectionConfigReadRow(
            version=c.config_version,
            endpoint=c.endpoint,
            settings=c.settings,
        ),
        config_revision=c.config_revision,
        identity=identity,
        verification=VerificationReadRow(
            job_id=verification.job_id,
            config_revision=verification.config_revision,
            status=verification.status,
            checked_at=verification.checked_at,
            error_code=verification.error_code,
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

"""Преобразование SQL-строк в безопасные проекции чтения."""

from src.modules.channels.application.port.query_repository import (
    ChannelReadRow,
    ConnectionConfigReadRow,
    ResourceIdentityReadRow,
    VerificationReadRow,
)
from src.modules.channels.infrastructure.persistence.models.channel import (
    ChannelModel,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.verification_document import (
    VerificationDocument,
)


def to_read_row(row: ChannelModel, connection_row: ConnectionModel) -> ChannelReadRow:
    """Читает публичные примитивы без восстановления и сериализации Domain VO."""
    verification = VerificationDocument.model_validate(connection_row.verification)
    identity = (
        ResourceIdentityReadRow(
            namespace=connection_row.identity_namespace, key=connection_row.identity_key
        )
        if connection_row.identity_namespace is not None
        and connection_row.identity_key is not None
        else None
    )
    return ChannelReadRow(
        id=row.id,
        name=row.name,
        platform_kind=row.platform_kind,
        revision=row.revision,
        config=ConnectionConfigReadRow(
            version=connection_row.config_version,
            endpoint=connection_row.endpoint,
            settings=connection_row.settings,
        ),
        config_revision=connection_row.config_revision,
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

from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.connection import Connection
from src.modules.channels.domain.error import InvalidResourceIdentityError
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
from src.modules.channels.infrastructure.persistence.verification_document import (
    VerificationDocument,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


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
    namespace = row.identity_namespace
    key = row.identity_key
    if namespace is None and key is None:
        return None
    if namespace is None or key is None:
        raise InvalidResourceIdentityError(
            "Не удалось определить идентификатор магазина."
        )
    return ResourceIdentityVO(namespace=namespace, key=key)


def to_domain(row: ChannelModel, connection_row: ConnectionModel) -> Channel:
    """Восстанавливает Entity и Aggregate через явные фабрики."""
    connection = Connection.restore(
        connection_id=EntityIdVO.from_value(connection_row.id),
        config=ConnectionConfigVO.create(
            version=connection_row.config_version,
            endpoint=connection_row.endpoint,
            settings=connection_row.settings,
        ),
        encrypted_credentials=connection_row.encrypted_credentials,
        config_revision=connection_row.config_revision,
        identity=read_identity(connection_row),
        verification=read_verification(connection_row),
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


def write_channel(row: ChannelModel, channel: Channel) -> None:
    """Переносит поля корня в SQL-модель без выполнения запросов."""
    row.name = channel.name.value
    row.platform_kind = channel.platform_kind
    row.revision = channel.revision
    row.created_at = channel.created_at
    row.updated_at = channel.updated_at
    row.created_by = channel.created_by.uuid
    row.updated_by = channel.updated_by.uuid


def write_connection(stored: ConnectionModel, connection: Connection) -> None:
    """Переносит поля принадлежащего подключения в SQL-модель без I/O."""
    stored.config_version = connection.config.version
    stored.endpoint = connection.config.endpoint
    stored.settings = connection.config.settings
    stored.encrypted_credentials = connection.encrypted_credentials
    stored.config_revision = connection.config_revision
    stored.identity_namespace = (
        connection.identity.namespace if connection.identity else None
    )
    stored.identity_key = connection.identity.key if connection.identity else None
    stored.verification = write_verification(connection.verification)

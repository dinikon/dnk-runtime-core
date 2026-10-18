from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.external_publication.value_object.core import (
    PublicationCoreVO,
    JsonValue,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)


@dataclass(slots=True)
class ExternalPublication:
    """Владеет последним наблюдаемым состоянием одной внешней карточки."""

    id: EntityIdVO
    connection_id: EntityIdVO
    core: PublicationCoreVO
    extension_version: str
    extensions: dict[str, JsonValue]
    fingerprint: str
    observed_revision: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_import_run_id: EntityIdVO

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        core: PublicationCoreVO,
        extension_version: str,
        extensions: dict[str, JsonValue],
        fingerprint: str,
        run_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт наблюдение без записи в Catalog."""
        return cls.restore(
            identifier,
            connection_id,
            core,
            extension_version,
            extensions,
            fingerprint,
            1,
            now,
            now,
            run_id,
        )

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        core: PublicationCoreVO,
        extension_version: str,
        extensions: dict[str, JsonValue],
        fingerprint: str,
        observed_revision: int,
        first_seen_at: datetime,
        last_seen_at: datetime,
        last_import_run_id: EntityIdVO,
    ) -> Self:
        """Восстанавливает сохранённое наблюдение с прежней версией."""
        if observed_revision < 1 or not extension_version or (not fingerprint):
            raise ChannelsValidationError("invalid_publication_state")
        return cls(
            identifier,
            connection_id,
            core,
            extension_version,
            extensions,
            fingerprint,
            observed_revision,
            first_seen_at,
            last_seen_at,
            last_import_run_id,
        )

    def observe(
        self,
        core: PublicationCoreVO,
        extension_version: str,
        extensions: dict[str, JsonValue],
        fingerprint: str,
        run_id: EntityIdVO,
        now: datetime,
    ) -> None:
        """Обновляет observed, сохраняя внутренний ID и первую отметку времени."""
        if (self.core.resource_type, self.core.external_id) != (
            core.resource_type,
            core.external_id,
        ):
            raise ChannelsConflictError("publication_identity_changed")
        if self.fingerprint != fingerprint:
            self.observed_revision += 1
        self.core, self.extension_version, self.extensions = (
            core,
            extension_version,
            extensions,
        )
        self.fingerprint, self.last_seen_at, self.last_import_run_id = (
            fingerprint,
            now,
            run_id,
        )

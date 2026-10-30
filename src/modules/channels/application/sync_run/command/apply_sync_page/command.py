from datetime import datetime

"""Результат внешнего API, применяемый с повторной проверкой поколения."""

from dataclasses import dataclass

from src.modules.channels.application.sync_run.port.jobs import SyncJob
from src.modules.channels.application.sync_run.port.source import PublicationPage
from src.modules.channels.domain.external_publication.value_object import (
    PublicationKind,
)


@dataclass(frozen=True, slots=True)
class ApplySyncPageCommand:
    """Передаёт страницу либо окончательную безопасную ошибку."""

    job: SyncJob
    lock_token: str
    expected_revision: int
    page: PublicationPage | None
    parent_kind: PublicationKind | None
    error_code: str | None = None
    source_started_at: datetime | None = None

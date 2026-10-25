from datetime import datetime, timedelta
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


def can_resume_import(
    *,
    status: str,
    has_source: bool,
    version: int,
    prepared_version: int,
    total: int,
    processed: int,
    finished_at: datetime | None,
    now: datetime,
    source_lifetime: timedelta,
    configuration: ImportConfiguration,
) -> bool:
    """Разрешает продолжение остановленного подготовленного снимка до его истечения."""
    available = (
        status == "cancelled"
        and has_source
        and prepared_version == version
        and total > processed
        and finished_at is not None
        and now < finished_at + source_lifetime
    )
    if not available:
        return False
    try:
        configuration.ensure_startable()
    except InvalidCatalogValueError:
        return False
    return True

from dataclasses import fields, is_dataclass
from contextlib import contextmanager
from fastapi import HTTPException
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.error import (
    PriceListNotFoundError,
    PriceListStateConflict,
)
from src.modules.price_lists.domain.offer.error import OfferNotFoundError
from src.modules.price_lists.domain.sync_run.error import SyncRunNotFoundError
from src.modules.price_lists.infrastructure.source.fetcher import SourceDownloadError
from src.modules.price_lists.infrastructure.persistence.base import (
    PersistenceMappingError,
)
from sqlalchemy.exc import IntegrityError


def context_ids(context):
    """Извлекает tenant и actor только из доверенного контекста."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    return EntityIdVO.from_value(principal.tenant_id), EntityIdVO.from_value(
        principal.user_id
    )


def dto_values(value):
    """Явно преобразует DTO/VO в значения response schemas."""
    if isinstance(value, EntityIdVO):
        return value.uuid
    if is_dataclass(value):
        return {
            field.name: dto_values(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, (list, tuple)):
        return [dto_values(item) for item in value]
    if isinstance(value, dict):
        return {key: dto_values(item) for key, item in value.items()}
    return value


@contextmanager
def http_errors():
    """Разделяет domain validation, not-found и infrastructure conflicts."""
    try:
        yield
    except (PriceListNotFoundError, OfferNotFoundError, SyncRunNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except PriceListStateConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    except SourceDownloadError as exc:
        raise HTTPException(422, "Source could not be downloaded.") from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Concurrent data conflict.") from exc
    except PersistenceMappingError as exc:
        raise HTTPException(500, "Invalid persisted price-list data.") from exc


__all__ = ["context_ids", "dto_values", "http_errors"]

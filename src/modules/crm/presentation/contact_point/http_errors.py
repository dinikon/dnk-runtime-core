from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.modules.contact_points.domain.binding.error import (
    InvalidContactPointBindingError,
)
from src.modules.contact_points.infrastructure.persistence.base import (
    ContactPointPersistenceMappingError,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.shared.domain.domain_error import DomainError


@contextmanager
def contact_point_http_errors():
    """Сохраняет адрес строки ошибки и отдаёт rollback внешнему UoW."""
    try:
        yield
    except (ContactNotFoundError, CompanyNotFoundError):
        raise
    except InvalidContactPointBindingError as exc:
        raise HTTPException(
            422,
            [
                {
                    "loc": ["body", exc.array, exc.index, exc.field],
                    "msg": str(exc),
                    "type": "value_error",
                }
            ],
        ) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "Конфликт контактных данных.") from exc
    except ContactPointPersistenceMappingError as exc:
        raise HTTPException(500, "Invalid persisted contact point data.") from exc

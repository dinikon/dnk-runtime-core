from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.modules.crm.domain.sales_error import SalesConflictError, SalesNotFoundError
from src.modules.funnel.domain.error import FunnelConflictError, FunnelNotFoundError
from src.modules.catalog.domain.error import CatalogNotFoundError


def sales_http_error(error: Exception) -> HTTPException:
    """Переводит ожидаемый отказ, не раскрывая SQL и чужие данные."""
    if isinstance(error, (SalesConflictError, FunnelConflictError, IntegrityError)):
        return HTTPException(
            409,
            (
                "Конфликт состояния. Обновите данные."
                if isinstance(error, IntegrityError)
                else str(error)
            ),
        )
    if isinstance(
        error, (SalesNotFoundError, FunnelNotFoundError, CatalogNotFoundError)
    ):
        return HTTPException(404, "Запись не найдена в текущем пространстве.")
    return HTTPException(422, str(error) or "Некорректное значение.")

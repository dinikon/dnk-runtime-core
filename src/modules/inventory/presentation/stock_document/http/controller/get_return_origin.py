from uuid import UUID
from fastapi import HTTPException
from src.modules.shared.domain.domain_error import DomainError
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError
from src.modules.inventory.application.stock_document.query.get_return_origin.query import (
    GetReturnOriginQuery,
)
from src.modules.inventory.presentation.stock_document.return_depends import (
    GetReturnOriginHandlerDep,
)
from src.modules.inventory.presentation.stock_document.http.response.get_return_origin import (
    GetReturnOriginResponse,
)


async def get_return_origin(
    identifier: UUID, handler: GetReturnOriginHandlerDep
) -> GetReturnOriginResponse:
    """Читает контекст возврата только по допустимому факту выбранного tenant."""
    try:
        result = await handler.execute(GetReturnOriginQuery(identifier))
    except StockDocumentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(422, str(exc)) from exc
    return GetReturnOriginResponse.from_dto(result)

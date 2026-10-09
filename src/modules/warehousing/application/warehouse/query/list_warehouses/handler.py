from src.modules.warehousing.application.warehouse.port.query_repository import (
    WarehouseQueryRepositoryProtocol,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.cursor import (
    WarehouseListCursor,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.dto import (
    ListWarehousesResultDTO,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.error import (
    InvalidWarehouseListParametersError,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.warehousing.domain.warehouse.value_object.status import WarehouseStatus
from src.modules.warehousing.domain.warehouse.value_object.warehouse_type import (
    WarehouseTypeVO,
)


class ListWarehousesHandler:
    """Собирает страницу из проекций без восстановления агрегатов."""

    def __init__(self, repository: WarehouseQueryRepositoryProtocol) -> None:
        """Принимает read repository общего tenant UoW."""
        self._repository = repository

    async def execute(self, query: ListWarehousesQuery) -> ListWarehousesResultDTO:
        """Проверяет параметры и возвращает не более limit строк с next_cursor."""
        if type(query.limit) is not int or not 1 <= query.limit <= 100:
            raise InvalidWarehouseListParametersError(
                "limit должен быть целым числом от 1 до 100."
            )
        try:
            status = None if query.status is None else WarehouseStatus(query.status)
        except (ValueError, TypeError) as exc:
            raise InvalidWarehouseListParametersError(
                "Неизвестный status склада."
            ) from exc
        warehouse_type = (
            None
            if query.warehouse_type is None
            else WarehouseTypeVO(query.warehouse_type)
        )
        cursor = (
            None if query.cursor is None else WarehouseListCursor.decode(query.cursor)
        )
        rows = await self._repository.list_items(
            tenant_id=query.tenant_id,
            status=status,
            warehouse_type=warehouse_type,
            cursor=cursor,
            limit=query.limit + 1,
        )
        items = rows[: query.limit]
        next_cursor = None
        if len(rows) > query.limit:
            last = items[-1]
            next_cursor = WarehouseListCursor(last.code, last.id).encode()
        return ListWarehousesResultDTO(items=items, next_cursor=next_cursor)

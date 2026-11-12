from typing import Annotated

from fastapi import Depends

from src.modules.inventory.application.uom.query.list_uoms.handler import (
    ListUomsHandler,
)


def get_list_uoms_handler() -> ListUomsHandler:
    """Собирает чтение системных единиц без открытия сессии хранения."""
    return ListUomsHandler()


ListUomsHandlerDep = Annotated[ListUomsHandler, Depends(get_list_uoms_handler)]

from fastapi import Request
from sqlalchemy import text
from src.modules.shared.presentation.persistence.depends import UoWDep


async def prepare_catalog_transaction(request: Request, uow: UoWDep) -> None:
    """Настраивает read snapshot до SQL зависимостей Identity на общем UoW."""
    if request.method in {"GET", "HEAD"}:
        await uow.session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        )

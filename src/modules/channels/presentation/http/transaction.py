"""Один согласованный снимок для составных read-проекций Channels."""

from fastapi import Request
from sqlalchemy import text
from src.modules.shared.presentation.persistence.depends import UoWDep


async def prepare_channels_read(request: Request, uow: UoWDep) -> None:
    """Выбирает изоляцию до SQL зависимостей Identity, не блокируя команды."""
    if request.method in {"GET", "HEAD"} or request.url.path.endswith(
        "/catalog-bindings/preview"
    ):
        await uow.session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        )

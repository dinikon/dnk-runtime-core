from sqlalchemy import delete, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.currency.domain.aggregate import ExchangeRateBook
from src.modules.currency.infrastructure.persistence.mapper import (
    ExchangeRateBookMapper,
)
from src.modules.currency.infrastructure.persistence.models.exchange_rate_book import (
    ExchangeRateBookModel,
)
from src.modules.currency.infrastructure.persistence.models.exchange_rate_quote import (
    ExchangeRateQuoteModel,
)


class SqlAlchemyExchangeRateBookRepository:
    """Хранит книгу целиком на сессии внешнего UoW под блокировкой публикации."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW с заранее привязанной tenant-схемой."""
        self._session = session

    async def get(self) -> ExchangeRateBook | None:
        """Загружает книгу и её котировки для изменения агрегата."""
        books = ExchangeRateBookModel.__table__
        row = (
            (await self._session.execute(select(books).where(books.c.source == "nbu")))
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        quotes = ExchangeRateQuoteModel.__table__
        quote_rows = (
            (
                await self._session.execute(
                    select(quotes)
                    .where(quotes.c.book_source == "nbu")
                    .order_by(quotes.c.source_currency)
                )
            )
            .mappings()
            .all()
        )
        return ExchangeRateBookMapper.to_domain(row, quote_rows)

    async def save(self, book: ExchangeRateBook) -> None:
        """Записывает метаданные и заменяет набор котировок в общей транзакции."""
        books = ExchangeRateBookModel.__table__
        quotes = ExchangeRateQuoteModel.__table__
        values = ExchangeRateBookMapper.to_book_values(book)
        statement = pg_insert(books).values(values)
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[books.c.source],
                set_={key: value for key, value in values.items() if key != "source"},
            )
        )
        await self._session.execute(delete(quotes).where(quotes.c.book_source == "nbu"))
        await self._session.execute(
            insert(quotes), ExchangeRateBookMapper.to_quote_values(book)
        )

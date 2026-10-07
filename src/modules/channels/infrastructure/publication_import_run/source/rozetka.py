import asyncio
import hashlib
import json
from typing import Any
from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourceConnection,
    PublicationSourcePage,
)
from src.modules.channels.infrastructure.publication_import_run.source.http_client import (
    PublicationJsonClient,
)
from src.modules.channels.infrastructure.publication_import_run.source.rozetka_auth import (
    RozetkaSession,
)
from src.modules.channels.infrastructure.publication_import_run.source.rozetka_normalizer import (
    RozetkaPublicationNormalizer,
    item_id,
)

PAGE_SIZE = 20
STREAMS = (
    ("/goods/all", 0),
    ("/goods/all", 1),
    ("/goods/all", 2),
    ("/goods/archive", None),
)


def cursor_from(checkpoint: str) -> dict[str, Any]:
    """Восстанавливает ограниченный курсор версии один без секретов и токена."""
    try:
        cursor = json.loads(checkpoint)
    except (TypeError, ValueError):
        raise PublicationSourceError("invalid_source_data") from None
    if cursor == {}:
        return {
            "version": 1,
            "stream": 0,
            "page": 1,
            "pending": [],
            "more": False,
            "recent": [],
        }
    if not isinstance(cursor, dict) or set(cursor) != {
        "version",
        "stream",
        "page",
        "pending",
        "more",
        "recent",
    }:
        raise PublicationSourceError("invalid_source_data")
    if (
        type(cursor["version"]) is not int
        or cursor["version"] != 1
        or type(cursor["stream"]) is not int
        or not 0 <= cursor["stream"] < len(STREAMS)
        or type(cursor["page"]) is not int
        or not 1 <= cursor["page"] <= 1_000_000
        or type(cursor["more"]) is not bool
        or not isinstance(cursor["pending"], list)
        or len(cursor["pending"]) > PAGE_SIZE
        or any(not isinstance(row, dict) for row in cursor["pending"])
        or not isinstance(cursor["recent"], list)
        or len(cursor["recent"]) > 64
        or any(
            not isinstance(value, str) or len(value) != 64 for value in cursor["recent"]
        )
    ):
        raise PublicationSourceError("invalid_source_data")
    return cursor


def list_page(
    content: dict[str, Any], page: int, recent: list[str]
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Проверяет страницу и метаданные; повтор выдачи считается остановкой пагинации."""
    rows, meta = content.get("items"), content.get("_meta")
    if (
        not isinstance(rows, list)
        or len(rows) > PAGE_SIZE
        or any(not isinstance(row, dict) for row in rows)
        or not isinstance(meta, dict)
        or any(
            type(meta.get(key)) is not int
            for key in ("currentPage", "pageCount", "perPage", "totalCount")
        )
    ):
        raise PublicationSourceError("invalid_source_data")
    if (
        meta["currentPage"] != page
        or meta["pageCount"] < 0
        or meta["perPage"] != PAGE_SIZE
        or meta["totalCount"] < len(rows)
        or (rows and meta["pageCount"] < page)
    ):
        raise PublicationSourceError("pagination_stalled")
    identities = [item_id(row) for row in rows]
    if len(identities) != len(set(identities)):
        raise PublicationSourceError("pagination_stalled")
    more = page < meta["pageCount"]
    if not rows and (more or meta["totalCount"] > 0):
        raise PublicationSourceError("pagination_stalled")
    fingerprint = (
        hashlib.sha256(json.dumps(identities).encode()).hexdigest() if rows else None
    )
    if fingerprint is not None and fingerprint in recent:
        raise PublicationSourceError("pagination_stalled")
    return rows, more, fingerprint


def detail_item(content: dict[str, Any], identity: int) -> dict[str, Any]:
    """Разбирает объект либо одиночный массив деталей с совпадающим внутренним ID."""
    value = content.get("item")
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, dict) or item_id(value) != identity:
        raise PublicationSourceError("invalid_source_data")
    return value


class RozetkaPublicationSource:
    """Обходит кабинет и архив, сохраняя одну полную карточку за фоновую порцию."""

    def __init__(
        self,
        client: PublicationJsonClient,
        normalizer: RozetkaPublicationNormalizer,
        budget_seconds: float = 60,
    ) -> None:
        """Принимает сетевой адаптер, нормализатор и общий бюджет меньше аренды worker."""
        self._client, self._normalizer, self._budget = (
            client,
            normalizer,
            budget_seconds,
        )

    async def read_page(
        self, connection: PublicationSourceConnection, checkpoint: str
    ) -> PublicationSourcePage:
        """Ограничивает суммарное время login/list/detail, включая обновление токена."""
        try:
            async with asyncio.timeout(self._budget):
                return await self._read_page(connection, cursor_from(checkpoint))
        except TimeoutError:
            raise PublicationSourceError("source_unavailable", retryable=True) from None

    async def _read_page(
        self, connection: PublicationSourceConnection, cursor: dict[str, Any]
    ) -> PublicationSourcePage:
        """Использует сохранённый остаток страницы и атомарно возвращает следующий курсор."""
        session = RozetkaSession(self._client, connection)
        if not cursor["pending"]:
            path, available = STREAMS[cursor["stream"]]
            params: dict[str, str | int] = {
                "page": cursor["page"],
                "pageSize": PAGE_SIZE,
                "sort": "price_offer_id",
            }
            if available is not None:
                params["available"] = available
            response = await session.get(path, params)
            rows, more, fingerprint = list_page(
                response, cursor["page"], cursor["recent"]
            )
            cursor["pending"], cursor["more"] = rows, more
            if fingerprint:
                cursor["recent"] = (cursor["recent"] + [fingerprint])[-64:]
        resources = ()
        if cursor["pending"]:
            listing = cursor["pending"][0]
            identity = item_id(listing)
            params = {"item_id": identity}
            source_id = listing.get("sync_source_id")
            if type(source_id) is int and source_id > 0:
                params["sync_source_id"] = source_id
            response = await session.get("/goods/details", params)
            resources = (
                self._normalizer.normalize(listing, detail_item(response, identity)),
            )
            cursor["pending"] = cursor["pending"][1:]
        if not cursor["pending"]:
            if cursor["more"]:
                cursor["page"] += 1
            else:
                cursor["stream"] += 1
                cursor["page"], cursor["recent"] = 1, []
                if cursor["stream"] == len(STREAMS):
                    return PublicationSourcePage(resources, None)
        return PublicationSourcePage(
            resources, json.dumps(cursor, ensure_ascii=False, sort_keys=True)
        )

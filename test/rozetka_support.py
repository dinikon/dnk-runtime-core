"""Документированные формы ответов Rozetka для контрактных и PostgreSQL-проверок."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
import httpx


def read_fixture() -> dict[str, Any]:
    """Возвращает независимую копию синтетической карточки из официального контракта."""
    return json.loads(
        (Path(__file__).parent / "fixtures/rozetka/read.json").read_text()
    )


class RozetkaFixtureApi:
    """Имитирует две страницы, разные прайсы и пересечение архива с общим списком."""

    def __init__(self) -> None:
        """Создаёт счётчик авторизаций и журнал безопасных тестовых запросов."""
        self.logins = 0
        self.requests: list[httpx.Request] = []
        self.fixture = read_fixture()

    def row(self, identity: int) -> dict[str, Any]:
        """Разводит технические ID и источники, не требуя публичного ID площадки."""
        row = deepcopy(self.fixture["list_item"])
        row["item_id"] = identity
        row["sync_source_id"] = 199 + identity % 2
        row["price_offer_id"] = str(identity)
        if identity in (13, 15):
            row.update(
                available=1 if identity == 13 else 0,
                upload_status=15,
                upload_status_title="Архівний",
            )
        if identity == 14:
            row.update(available=2, upload_status=15, upload_status_title="Архівний")
        return row

    def handle(self, request: httpx.Request) -> httpx.Response:
        """Возвращает строго разделённые auth/list/detail envelopes."""
        self.requests.append(request)
        assert request.url.host == "api-seller.rozetka.com.ua"
        assert request.headers["Content-Language"] == "uk"
        if request.url.path == "/sites":
            assert request.method == "POST"
            self.logins += 1
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "content": {"access_token": f"fixture-token-{self.logins}"},
                },
            )
        assert request.method == "GET"
        assert request.headers["Authorization"] == f"Bearer fixture-token-{self.logins}"
        if request.url.path == "/goods/details":
            identity = int(request.url.params["item_id"])
            details = deepcopy(self.fixture["detail_item"])
            details.update(
                item_id=identity,
                sync_source_id=self.row(identity)["sync_source_id"],
                price_offer_id=str(identity),
            )
            return httpx.Response(
                200, json={"success": True, "content": {"item": [details]}}
            )
        page = int(request.url.params["page"])
        available = request.url.params.get("available")
        if request.url.path == "/goods/archive":
            ids, pages, total = [13, 15], 1, 2
        elif available == "1":
            ids, pages, total = ([11, 12] if page == 1 else [13]), 2, 3
        elif available == "2":
            ids, pages, total = [14], 1, 1
        else:
            ids, pages, total = [], 0, 0
        rows = [self.row(identity) for identity in ids]
        return httpx.Response(
            200,
            json={
                "success": True,
                "content": {
                    "items": rows,
                    "count": len(rows),
                    "_meta": {
                        "currentPage": page,
                        "pageCount": pages,
                        "perPage": 20,
                        "totalCount": total,
                    },
                },
            },
        )

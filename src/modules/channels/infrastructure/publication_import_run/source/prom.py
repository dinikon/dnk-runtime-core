import json
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
from src.modules.channels.infrastructure.publication_import_run.source.normalizer import (
    PublicationNormalizer,
)


class PromPublicationSource:
    """Читает native карточки Prom со всех страниц GET products/list."""

    def __init__(
        self, client: PublicationJsonClient, normalizer: PublicationNormalizer
    ) -> None:
        """Принимает ограниченный JSON клиент и нормализатор карточек."""
        self._client, self._normalizer = client, normalizer

    async def read_page(
        self, connection: PublicationSourceConnection, checkpoint: str
    ) -> PublicationSourcePage:
        """Обходит ID в убывающем порядке, сохраняя отдельные публикации Prom."""
        cursor = json.loads(checkpoint)
        params: dict[str, str | int] = {"limit": 100}
        if "last_id" in cursor:
            params["last_id"] = cursor["last_id"]
        token = connection.secrets.get("api_key")
        if not token:
            raise PublicationSourceError("access_denied")
        payload, _ = await self._client.get(
            "https://my.prom.ua/api/v1/products/list",
            headers={"Authorization": "Bearer " + token},
            params=params,
        )
        if not isinstance(payload, dict) or not isinstance(
            payload.get("products"), list
        ):
            raise PublicationSourceError("invalid_source_data")
        rows = payload["products"]
        if any(not isinstance(row, dict) for row in rows) or len(rows) > 100:
            raise PublicationSourceError("invalid_source_data")
        resources = tuple(self._normalizer.normalize("prom", row) for row in rows)
        ids = [int(resource.external_id) for resource in resources]
        if len(set(ids)) != len(ids) or (
            ids and "last_id" in cursor and max(ids) > cursor["last_id"]
        ):
            raise PublicationSourceError("pagination_stalled")
        next_checkpoint = None
        if len(rows) == 100:
            last_id = min(ids) - 1
            if last_id <= 0:
                return PublicationSourcePage(resources, None)
            if "last_id" in cursor and last_id >= cursor["last_id"]:
                raise PublicationSourceError("pagination_stalled")
            next_checkpoint = json.dumps({"last_id": last_id}, sort_keys=True)
        return PublicationSourcePage(resources, next_checkpoint)

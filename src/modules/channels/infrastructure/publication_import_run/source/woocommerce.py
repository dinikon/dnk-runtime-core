import base64
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
    text,
)


class WooPublicationSource:
    """Читает REST карточки Woo и страницы вариаций без усечения дочерних ресурсов."""

    def __init__(
        self, client: PublicationJsonClient, normalizer: PublicationNormalizer
    ) -> None:
        """Принимает JSON клиент и отдельный нормализатор Read документа."""
        self._client, self._normalizer = client, normalizer

    async def read_page(
        self, connection: PublicationSourceConnection, checkpoint: str
    ) -> PublicationSourcePage:
        """Чередует страницу родителей с полным обходом вариаций каждого родителя."""
        cursor = json.loads(checkpoint)
        base = connection.public.get("url", "").rstrip("/") + "/wp-json/wc/v3"
        key, secret = connection.secrets.get("consumer_key"), connection.secrets.get(
            "consumer_secret"
        )
        if not key or not secret:
            raise PublicationSourceError("access_denied")
        headers = {
            "Authorization": "Basic "
            + base64.b64encode((key + ":" + secret).encode()).decode()
        }
        if "currency" not in cursor:
            currency = None
            try:
                setting, _ = await self._client.get(
                    base + "/settings/general/woocommerce_currency",
                    headers=headers,
                    params={},
                )
                currency = (
                    text(setting.get("value")) if isinstance(setting, dict) else None
                )
            except PublicationSourceError:
                # Reading products may be permitted while reading store settings is denied.
                pass
            cursor["currency"] = currency
        parent_ids = cursor.get("parents") or []
        parent_id = str(parent_ids[0]) if parent_ids else None
        page = cursor.get("variation_page", 1) if parent_id else cursor.get("page", 1)
        path = "/products/" + parent_id + "/variations" if parent_id else "/products"
        params: dict[str, str | int] = {
            "per_page": 100,
            "page": page,
            "orderby": "id",
            "order": "asc",
        }
        if not parent_id:
            params["status"] = "any"
        rows, response_headers = await self._client.get(
            base + path, headers=headers, params=params
        )
        if (
            not isinstance(rows, list)
            or any(not isinstance(row, dict) for row in rows)
            or len(rows) > 100
        ):
            raise PublicationSourceError("invalid_source_data")
        resources = tuple(
            self._normalizer.normalize(
                "woocommerce", row, currency=cursor["currency"], parent_id=parent_id
            )
            for row in rows
        )
        ids = [int(resource.external_id) for resource in resources]
        previous_id = cursor.get(
            "last_variation_id" if parent_id else "last_product_id", 0
        )
        if len(set(ids)) != len(ids) or (ids and min(ids) <= previous_id):
            raise PublicationSourceError("pagination_stalled")
        total = response_headers.get("x-wp-totalpages")
        more = page < int(total) if total and total.isdigit() else len(rows) == 100
        if more and not ids:
            raise PublicationSourceError("pagination_stalled")
        if parent_id:
            if more:
                cursor["variation_page"] = page + 1
                cursor["last_variation_id"] = max(ids)
            else:
                cursor["parents"] = parent_ids[1:]
                cursor["variation_page"] = 1
                cursor.pop("last_variation_id", None)
            if not cursor.get("parents") and not cursor.get("more_products"):
                return PublicationSourcePage(resources, None)
        else:
            cursor["parents"] = [
                row["id"] for row in rows if row.get("type") == "variable"
            ]
            cursor["variation_page"] = 1
            cursor["page"] = page + 1
            cursor["more_products"] = more
            if ids:
                cursor["last_product_id"] = max(ids)
            if not cursor["parents"] and not more:
                return PublicationSourcePage(resources, None)
        return PublicationSourcePage(resources, json.dumps(cursor, sort_keys=True))

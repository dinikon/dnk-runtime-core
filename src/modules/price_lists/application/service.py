from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter

from src.modules.price_lists.domain import (
    PriceListStatus,
    SourceFormat,
    mask_source_url,
)
from src.modules.price_lists.infrastructure.persistence import (
    SqlAlchemyPriceListRepository,
)
from src.modules.price_lists.infrastructure.source import (
    HttpRemoteFileFetcher,
    SourceUrlCipher,
    SourceParser,
    prom_xml_config,
)


class PriceListStateConflict(ValueError):
    """Raised when a lifecycle state does not allow a requested mutation."""


def next_cron_occurrence(
    expression: str,
    timezone: str,
    *,
    after: datetime | None = None,
) -> datetime:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown timezone.") from exc
    base = (after or datetime.now(UTC)).astimezone(zone)
    if not croniter.is_valid(expression):
        raise ValueError("Invalid CRON expression.")
    return croniter(expression, base).get_next(datetime).astimezone(UTC)


def cron_occurrences(
    expression: str,
    timezone: str,
    *,
    count: int = 5,
    after: datetime | None = None,
) -> list[datetime]:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown timezone.") from exc
    if not croniter.is_valid(expression):
        raise ValueError("Invalid CRON expression.")
    iterator = croniter(expression, (after or datetime.now(UTC)).astimezone(zone))
    occurrences = [
        iterator.get_next(datetime).astimezone(UTC) for _ in range(max(count, 2))
    ]
    if occurrences[1] - occurrences[0] < timedelta(minutes=15):
        raise ValueError("CRON frequency must be at least 15 minutes.")
    return occurrences[:count]


class PriceListService:
    def __init__(
        self,
        repository: SqlAlchemyPriceListRepository,
        *,
        fetcher: HttpRemoteFileFetcher | None = None,
        parser: SourceParser | None = None,
    ) -> None:
        self.repository = repository
        self.fetcher = fetcher or HttpRemoteFileFetcher()
        self.parser = parser or SourceParser()

    async def create(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        title: str,
        source_format: str,
        source_preset: str | None,
        source_url: str,
        source_config: dict[str, Any],
    ) -> UUID:
        source_format = SourceFormat(source_format).value
        mapping: dict[str, Any] = {}
        if source_preset == "prom_xml":
            if source_format != SourceFormat.XML.value:
                raise ValueError("Prom preset requires XML format.")
            preset_source, mapping = prom_xml_config()
            source_config = {**preset_source, **source_config}
        _validate_source_config(source_format, source_config)
        return await self.repository.create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            title=title.strip(),
            source_format=source_format,
            source_preset=source_preset,
            source_url=SourceUrlCipher().encrypt(source_url),
            source_url_display=mask_source_url(source_url),
            source_config=source_config,
            mapping_config=mapping,
        )

    async def preview(
        self,
        tenant_id: UUID,
        price_list_id: UUID,
        *,
        candidate: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        price_list = await self._required(tenant_id, price_list_id)
        resolved = self._resolve_candidate(price_list, candidate or {})
        _validate_source_config(resolved["source_format"], resolved["source_config"])
        if resolved["mapping_config"]:
            _validate_mapping_config(resolved["mapping_config"])
        fetched = await self.fetcher.fetch(resolved["source_url"])
        try:
            inspection = self.parser.inspect(
                fetched.path,
                resolved["source_format"],
                resolved["source_config"],
            )
            rows = (
                [
                    {
                        "row_number": row.row_number,
                        "values": _json_values(row.normalized),
                        "errors": list(row.errors),
                    }
                    for row in self.parser.rows(
                        fetched.path,
                        resolved["source_format"],
                        resolved["source_config"],
                        resolved["mapping_config"],
                        limit=limit,
                    )
                ]
                if resolved["mapping_config"]
                else []
            )
            return {
                "format": resolved["source_format"],
                "content_type": fetched.content_type,
                "size": fetched.size,
                "checksum": fetched.checksum,
                **inspection,
                "rows": rows,
            }
        finally:
            Path(fetched.path).unlink(missing_ok=True)

    async def save_mapping(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        price_list_id: UUID,
        source_config: dict[str, Any],
        mapping_config: dict[str, Any],
    ) -> None:
        current = await self._required(tenant_id, price_list_id)
        _validate_source_config(current["source_format"], source_config)
        _validate_mapping_config(mapping_config)
        if current["status"] in {
            PriceListStatus.ACTIVE.value,
            PriceListStatus.ARCHIVED.value,
        }:
            raise PriceListStateConflict(
                "Pause or restore the price list before changing its mapping."
            )
        fetched = await self.fetcher.fetch(
            SourceUrlCipher().decrypt(current["source_url_secret"])
        )
        try:
            rows = list(
                self.parser.rows(
                    fetched.path,
                    current["source_format"],
                    source_config,
                    mapping_config,
                    limit=50,
                )
            )
            valid = [row for row in rows if not row.errors]
            external_ids = [
                str(row.normalized["external_id"])
                for row in rows
                if row.normalized.get("external_id") not in (None, "")
            ]
            if not valid:
                raise ValueError("Mapping preview has no valid rows.")
            if len(external_ids) != len(set(external_ids)):
                raise ValueError(
                    "Mapping preview contains duplicate external_id values."
                )
            if (len(rows) - len(valid)) / max(len(rows), 1) > 0.25:
                raise ValueError("Mapping preview validation threshold exceeded.")
        finally:
            Path(fetched.path).unlink(missing_ok=True)
        await self.repository.update_config(
            tenant_id=tenant_id,
            actor_id=actor_id,
            price_list_id=price_list_id,
            values={
                "source_config": source_config,
                "mapping_config": mapping_config,
                "mapping_version": int(current["mapping_version"]) + 1,
                "status": (
                    PriceListStatus.PAUSED.value
                    if current["status"] == PriceListStatus.PAUSED.value
                    else PriceListStatus.READY.value
                ),
            },
        )

    async def save_schedule(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        price_list_id: UUID,
        cron_expression: str,
        timezone: str,
        new_item_policy: str,
        missing_item_policy: str,
        missing_threshold: int,
    ) -> datetime:
        current = await self._required(tenant_id, price_list_id)
        if current["status"] in {
            PriceListStatus.ACTIVE.value,
            PriceListStatus.ARCHIVED.value,
        }:
            raise PriceListStateConflict(
                "Pause or restore the price list before changing its schedule."
            )
        next_at = cron_occurrences(cron_expression, timezone, count=1)[0]
        await self.repository.update_config(
            tenant_id=tenant_id,
            actor_id=actor_id,
            price_list_id=price_list_id,
            values={
                "cron_expression": cron_expression,
                "timezone": timezone,
                "new_item_policy": new_item_policy,
                "missing_item_policy": missing_item_policy,
                "missing_threshold": missing_threshold,
                "next_sync_at": (
                    None
                    if current["status"] == PriceListStatus.PAUSED.value
                    else next_at
                ),
                "schedule_revision": int(current["schedule_revision"]) + 1,
            },
        )
        return next_at

    async def update_settings(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        price_list_id: UUID,
        title: str,
        source_url: str | None,
        source_format: str,
        source_preset: str | None,
        source_config: dict[str, Any],
        mapping_config: dict[str, Any],
        cron_expression: str,
        timezone: str,
        new_item_policy: str,
        missing_item_policy: str,
        missing_threshold: int,
    ) -> None:
        current = await self._required(tenant_id, price_list_id)
        if current["status"] in {
            PriceListStatus.ACTIVE.value,
            PriceListStatus.ARCHIVED.value,
        }:
            raise PriceListStateConflict(
                "Pause or restore the price list before changing its settings."
            )
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Price-list title is required.")
        next_at = cron_occurrences(cron_expression, timezone, count=1)[0]
        candidate = self._resolve_candidate(
            current,
            {
                "source_url": source_url,
                "source_format": source_format,
                "source_preset": source_preset,
                "source_config": source_config,
                "mapping_config": mapping_config,
            },
        )
        _validate_source_config(candidate["source_format"], candidate["source_config"])
        _validate_mapping_config(candidate["mapping_config"])
        source_changed = any(
            candidate[key] != current[key]
            for key in (
                "source_format",
                "source_preset",
                "source_config",
                "mapping_config",
            )
        ) or (
            source_url is not None
            and candidate["source_url"]
            != SourceUrlCipher().decrypt(current["source_url_secret"])
        )
        if source_changed:
            await self._validate_candidate_file(candidate)
        values: dict[str, Any] = {
            "title": normalized_title,
            "source_format": candidate["source_format"],
            "source_preset": candidate["source_preset"],
            "source_config": candidate["source_config"],
            "mapping_config": candidate["mapping_config"],
            "cron_expression": cron_expression,
            "timezone": timezone,
            "new_item_policy": new_item_policy,
            "missing_item_policy": missing_item_policy,
            "missing_threshold": missing_threshold,
            "schedule_revision": int(current["schedule_revision"]) + 1,
            "next_sync_at": (
                None if current["status"] == PriceListStatus.PAUSED.value else next_at
            ),
            "status": (
                PriceListStatus.PAUSED.value
                if current["status"] == PriceListStatus.PAUSED.value
                else PriceListStatus.READY.value
            ),
        }
        if source_changed:
            values["mapping_version"] = int(current["mapping_version"]) + 1
        if source_url is not None:
            values.update(
                source_url_secret=SourceUrlCipher().encrypt(candidate["source_url"]),
                source_url_display=mask_source_url(candidate["source_url"]),
            )
        await self.repository.update_config(
            tenant_id=tenant_id,
            actor_id=actor_id,
            price_list_id=price_list_id,
            values=values,
        )

    def _resolve_candidate(
        self, current: dict[str, Any], candidate: dict[str, Any]
    ) -> dict[str, Any]:
        source_url = candidate.get("source_url") or SourceUrlCipher().decrypt(
            current["source_url_secret"]
        )
        source_format = SourceFormat(
            candidate.get("source_format", current["source_format"])
        ).value
        source_preset = candidate.get("source_preset", current["source_preset"])
        source_config = dict(
            candidate.get("source_config", current["source_config"]) or {}
        )
        mapping_config = dict(
            candidate.get("mapping_config", current["mapping_config"]) or {}
        )
        if source_preset == "prom_xml":
            if source_format != SourceFormat.XML.value:
                raise ValueError("Prom preset requires XML format.")
            preset_source, preset_mapping = prom_xml_config()
            source_config = {**preset_source, **source_config}
            mapping_config = mapping_config or preset_mapping
        return {
            "source_url": source_url,
            "source_format": source_format,
            "source_preset": source_preset,
            "source_config": source_config,
            "mapping_config": mapping_config,
        }

    async def _validate_candidate_file(self, candidate: dict[str, Any]) -> None:
        fetched = await self.fetcher.fetch(candidate["source_url"])
        try:
            rows = list(
                self.parser.rows(
                    fetched.path,
                    candidate["source_format"],
                    candidate["source_config"],
                    candidate["mapping_config"],
                    limit=50,
                )
            )
            valid = [row for row in rows if not row.errors]
            external_ids = [
                str(row.normalized["external_id"])
                for row in rows
                if row.normalized.get("external_id") not in (None, "")
            ]
            if not valid:
                raise ValueError("Mapping preview has no valid rows.")
            if len(external_ids) != len(set(external_ids)):
                raise ValueError(
                    "Mapping preview contains duplicate external_id values."
                )
            if (len(rows) - len(valid)) / max(len(rows), 1) > 0.25:
                raise ValueError("Mapping preview validation threshold exceeded.")
        finally:
            Path(fetched.path).unlink(missing_ok=True)

    async def _required(self, tenant_id: UUID, price_list_id: UUID) -> dict[str, Any]:
        result = await self.repository.get(tenant_id, price_list_id)
        if result is None:
            raise LookupError("Price list not found.")
        return result


def _json_values(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: str(value) if hasattr(value, "as_tuple") else value
        for key, value in values.items()
    }


def _validate_source_config(source_format: str, config: dict[str, Any]) -> None:
    if source_format in {SourceFormat.XML.value, SourceFormat.YAML.value}:
        path = str(config.get("item_path") or "")
        parts = path.split(".") if path else []
        if (
            not parts
            or len(parts) > 64
            or any(
                not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_:-]*", part) for part in parts
            )
        ):
            raise ValueError("A valid item_path is required.")
    if source_format == SourceFormat.XLSX.value:
        sheet = str(config.get("sheet_name") or "")
        header_row = int(config.get("header_row", 1))
        data_start = int(config.get("data_start_row", header_row + 1))
        if not sheet or len(sheet) > 31:
            raise ValueError("A valid XLSX sheet_name is required.")
        if not 1 <= header_row <= 10_000 or not header_row < data_start <= 10_001:
            raise ValueError("Invalid XLSX header/data row configuration.")


def _validate_mapping_config(mapping: dict[str, Any]) -> None:
    allowed_fields = {
        "external_id",
        "sku",
        "title",
        "purchase_price",
        "rrp",
        "currency",
        "availability",
        "quantity",
    }
    unknown = set(mapping) - allowed_fields
    if unknown:
        raise ValueError("Mapping contains unsupported target fields.")
    for field in ("external_id", "sku", "title", "purchase_price", "currency"):
        specification = mapping.get(field)
        if not isinstance(specification, dict) or not (
            specification.get("selector")
            or specification.get("selectors")
            or "constant" in specification
        ):
            raise ValueError(f"Mapping for {field} is required.")
    for specification in mapping.values():
        if not isinstance(specification, dict):
            raise ValueError("Mapping specifications must be objects.")
        selectors = specification.get("selectors") or [specification.get("selector")]
        if len(selectors) > 5 or any(
            selector is not None and len(str(selector)) > 255 for selector in selectors
        ):
            raise ValueError("Mapping selector limit exceeded.")

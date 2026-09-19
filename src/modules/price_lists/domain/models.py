from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import StrEnum
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid5

Identifier = UUID


class PriceListStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    INVALID = "invalid"
    ARCHIVED = "archived"


class SourceFormat(StrEnum):
    XML = "xml"
    YAML = "yaml"
    XLSX = "xlsx"


class Availability(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


class MappingValidationError(ValueError):
    """Raised when source or mapping configuration cannot produce valid offers."""


def normalize_availability(value: object, quantity: int | None = None) -> str:
    if quantity is not None:
        return (
            Availability.IN_STOCK.value
            if quantity > 0
            else Availability.OUT_OF_STOCK.value
        )
    normalized = str(value or "").strip().casefold()
    if normalized in {
        "1",
        "true",
        "yes",
        "y",
        "in_stock",
        "в наличии",
        "є в наявності",
        "наявний",
        "available",
    }:
        return Availability.IN_STOCK.value
    if normalized in {
        "0",
        "false",
        "no",
        "n",
        "out_of_stock",
        "нет в наличии",
        "немає в наявності",
        "відсутній",
        "unavailable",
    }:
        return Availability.OUT_OF_STOCK.value
    return Availability.UNKNOWN.value


def canonical_state_hash(
    *,
    purchase_price: Decimal,
    rrp: Decimal | None,
    currency: str,
    availability: str,
    quantity: int | None,
) -> str:
    payload = {
        "purchase_price": format(purchase_price, "f"),
        "rrp": None if rrp is None else format(rrp, "f"),
        "currency": currency.upper(),
        "availability": availability,
        "quantity": quantity,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


_JOB_NAMESPACE = UUID("bb04b5ea-0a10-4e36-93b9-40b77dbfa348")


def deterministic_job_id(
    tenant_id: Identifier,
    price_list_id: Identifier,
    schedule_revision: int,
    planned_at: str,
) -> Identifier:
    return uuid5(
        _JOB_NAMESPACE,
        f"{tenant_id}:{price_list_id}:{schedule_revision}:{planned_at}",
    )


def deterministic_cleanup_job_id(tenant_id: Identifier, planned_at: str) -> Identifier:
    return uuid5(_JOB_NAMESPACE, f"{tenant_id}:price-list-cleanup:{planned_at}")


def mask_source_url(value: str) -> str:
    parsed = urlsplit(value)
    segments = [segment for segment in parsed.path.split("/") if segment]
    path = "/…/" + segments[-1] if segments else "/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))

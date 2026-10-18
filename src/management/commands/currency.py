"""Команда ручного обновления tenant-книги NBU."""

from __future__ import annotations
import argparse
from uuid import UUID
from src.config import dnk_config
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable
import httpx
from src.modules.currency.presentation.management.refresh import refresh_exchange_rates
from src.modules.currency.application.error import (
    ExchangeRateSourceError,
    ExchangeRateCatalogMismatchError,
)
from src.modules.currency.domain.error import (
    InvalidExchangeRateError,
    InvalidExchangeRateSnapshotError,
    OlderExchangeRateSnapshotError,
)
from src.modules.shared.infrastructure.persistence.database_helper import db_helper


async def handle_refresh(args: argparse.Namespace) -> int:
    """Проверяет схему, обновляет книгу и выводит итог после commit."""
    try:
        await db_helper.initialize_for_startup()
        async with httpx.AsyncClient(timeout=10) as client:
            result = await refresh_exchange_rates(
                db_helper.session_factory,
                client=client,
                tenant_id=args.tenant_id,
                naming=TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
            )
        print(
            f"OK nbu tenant={args.tenant_id} snapshot={result.snapshot_id} quotes={result.quote_count} date={result.effective_date} checked_at={result.checked_at.isoformat()} excluded_unknown={result.excluded_unknown_count} excluded_metals={result.excluded_metal_count}"
        )
        return 0
    except (
        TenantUnavailable,
        ExchangeRateSourceError,
        ExchangeRateCatalogMismatchError,
        InvalidExchangeRateError,
        InvalidExchangeRateSnapshotError,
        OlderExchangeRateSnapshotError,
    ) as exc:
        print(f"FAILED currency refresh: {type(exc).__name__}")
        return 1
    finally:
        await db_helper.dispose()


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Регистрирует currency refresh без публичного HTTP endpoint."""
    parser = subparsers.add_parser("currency", help="Tenant NBU exchange rates")
    actions = parser.add_subparsers(dest="currency_command", required=True)
    refresh = actions.add_parser("refresh", help="Refresh the NBU exchange rate book")
    refresh.add_argument("--tenant-id", type=UUID, required=True, help="Tenant UUID")
    refresh.set_defaults(handler=handle_refresh)

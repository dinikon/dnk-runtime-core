from __future__ import annotations

import argparse
import sys
from uuid import UUID
from sqlalchemy import select
from src.config import dnk_config
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import DELETING
from src.modules.tenancy.presentation.depends.storage_management import (
    prepare_tenant_storage,
)


async def handle(args: argparse.Namespace) -> int:
    """Подготавливает системное хранилище существующих tenant или продолжает local onboarding."""
    failures = 0
    try:
        if args.all_tenants:
            async with db_helper.session_factory() as session:
                identifiers = list(
                    await session.scalars(
                        select(TenantModel.id)
                        .where(TenantModel.status.not_in(DELETING))
                        .order_by(TenantModel.id)
                    )
                )
        else:
            identifiers = [args.tenant_id]
        for identifier in identifiers:
            try:
                await prepare_tenant_storage(
                    db_helper.session_factory,
                    TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
                    identifier,
                    activate=args.files_action == "resume",
                )
            except Exception as exc:
                failures += 1
                print(
                    f"ERROR tenant_id={identifier} error_type={type(exc).__name__}",
                    file=sys.stderr,
                )
            else:
                print(f"OK tenant_id={identifier} storage_ready=true")
        return 2 if failures else 0
    finally:
        await db_helper.dispose()


def register(subparsers: argparse._SubParsersAction) -> None:
    """Регистрирует backfill хранилища и продолжение local onboarding."""
    files = subparsers.add_parser("files", help="Prepare private tenant storage.")
    actions = files.add_subparsers(dest="files_action", required=True)
    for name in ("prepare", "resume"):
        action = actions.add_parser(name)
        target = action.add_mutually_exclusive_group(required=True)
        target.add_argument("tenant_id", nargs="?", type=UUID)
        if name == "prepare":
            target.add_argument("--all", dest="all_tenants", action="store_true")
        action.set_defaults(handler=handle, all_tenants=False)

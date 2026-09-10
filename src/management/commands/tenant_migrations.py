import argparse
import sys
from uuid import UUID

from src.modules.tenancy.presentation.depends.management import (
    build_tenant_migration_management,
)


async def handle(args: argparse.Namespace) -> int:
    """Выполняет tenant-команду и сообщает ошибки отдельных tenants."""
    management = build_tenant_migration_management()
    if args.migration_action == "revision":
        try:
            script = await management.revision(args.tenant_id, args.message)
        except Exception as exc:
            print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        print(f"Generated {script.path}; review before applying.")
        return 0

    try:
        tenant_ids = (
            await management.list_ids() if args.all_tenants else [args.tenant_id]
        )
    except Exception as exc:
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    failures = 0
    for tenant_id in tenant_ids:
        try:
            result = await management.run_one(
                tenant_id, upgrade=args.migration_action == "upgrade"
            )
        except Exception as exc:
            failures += 1
            print(
                f"ERROR tenant_id={tenant_id} {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            continue
        print(
            f"OK tenant_id={result.tenant_id} schema_name={result.schema_name} current={','.join(result.revisions) or 'base'} head={result.head or 'base'}"
        )
    print(
        f"tenants={len(tenant_ids)} succeeded={len(tenant_ids) - failures} failed={failures}"
    )
    return 2 if failures else 0


def register(subparsers) -> None:
    """Регистрирует upgrade/current/revision для tenant Alembic environment."""
    parser = subparsers.add_parser(
        "tenant-migrations", help="Manage static tenant schemas with Alembic."
    )
    actions = parser.add_subparsers(dest="migration_action", required=True)
    for name in ("upgrade", "current"):
        action = actions.add_parser(name)
        target = action.add_mutually_exclusive_group(required=True)
        target.add_argument("tenant_id", nargs="?", type=UUID)
        target.add_argument("--all", dest="all_tenants", action="store_true")
        action.set_defaults(handler=handle)
    revision = actions.add_parser(
        "revision", help="Generate a draft using one existing tenant."
    )
    revision.add_argument("--autogenerate", action="store_true", required=True)
    revision.add_argument("--tenant-id", dest="tenant_id", type=UUID, required=True)
    revision.add_argument("-m", "--message", required=True)
    revision.set_defaults(handler=handle)

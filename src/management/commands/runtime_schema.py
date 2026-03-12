import argparse
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.infrastructure.factory import build_ddl_orchestrator
from src.modules.shared.db.helper import db_helper
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)


@dataclass(slots=True, frozen=True)
class _SyncTarget:
    tenant_id: UUID
    data_source_id: UUID
    schema: str


def register_runtime_schema_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    runtime_schema_parser = subparsers.add_parser(
        "runtime-schema",
        help="Runtime schema management commands.",
    )
    runtime_schema_subparsers = runtime_schema_parser.add_subparsers(
        dest="runtime_schema_command",
        required=True,
    )

    sync_parser = runtime_schema_subparsers.add_parser(
        "sync",
        help=(
            "Sync tenant runtime schemas with models from "
            "src/modules/runtime_schema/system_models/system_models.yaml."
        ),
    )
    sync_parser.add_argument(
        "--tenant-id",
        type=_parse_uuid,
        help="Tenant UUID. Use together with --data-source-id and --schema for a single target.",
    )
    sync_parser.add_argument(
        "--data-source-id",
        type=_parse_uuid,
        help="Data source UUID for a single target sync.",
    )
    sync_parser.add_argument(
        "--schema",
        type=str,
        help="Database schema for a single target sync.",
    )
    sync_parser.add_argument(
        "--manifest-path",
        type=Path,
        help="Optional custom path to runtime schema manifest yaml.",
    )
    sync_parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue syncing remaining tenants if one target fails.",
    )
    sync_parser.set_defaults(handler=_handle_sync_command)


async def _handle_sync_command(args: argparse.Namespace) -> int:
    explicit_single_target = any(
        value is not None
        for value in (args.tenant_id, args.data_source_id, args.schema)
    )
    if explicit_single_target and not all(
        value is not None
        for value in (args.tenant_id, args.data_source_id, args.schema)
    ):
        print(
            "error: for single target sync provide all: "
            "--tenant-id --data-source-id --schema"
        )
        return 2

    try:
        manifest_path = _resolve_manifest_path(args.manifest_path)
        targets = (
            [_SyncTarget(args.tenant_id, args.data_source_id, args.schema)]
            if explicit_single_target
            else await _load_all_targets()
        )
    except Exception as exc:
        print(f"error: unable to load sync targets: {exc}")
        return 1

    if not targets:
        print("No tenant data sources found. Nothing to sync.")
        return 0

    print(f"Found {len(targets)} target(s) to sync.")
    failures = 0
    for target in targets:
        try:
            result = await _sync_target(target=target, manifest_path=manifest_path)
            print(
                "OK"
                f" tenant={target.tenant_id}"
                f" data_source={target.data_source_id}"
                f" schema={target.schema}"
                f" version={result.version}"
                f" operations={result.applied_operations}"
            )
        except Exception as exc:
            failures += 1
            print(
                "FAILED"
                f" tenant={target.tenant_id}"
                f" data_source={target.data_source_id}"
                f" schema={target.schema}"
                f" error={exc}"
            )
            if not args.continue_on_error:
                break

    if failures:
        print(f"Sync finished with {failures} failure(s).")
        return 1
    print("Sync finished successfully.")
    return 0


async def _load_all_targets() -> list[_SyncTarget]:
    async with db_helper.session() as session:
        models = (
            await session.scalars(
                select(TenantDataSourceModel).order_by(
                    TenantDataSourceModel.created_at,
                    TenantDataSourceModel.tenant_id,
                )
            )
        ).all()
    return [
        _SyncTarget(
            tenant_id=_to_uuid(model.tenant_id),
            data_source_id=_to_uuid(model.id),
            schema=model.schema,
        )
        for model in models
    ]


async def _sync_target(
    *,
    target: _SyncTarget,
    manifest_path: Path | None,
):
    async with db_helper.session() as session:
        orchestrator = build_ddl_orchestrator(
            session=session,
            manifest_path=manifest_path,
        )
        result = await orchestrator.sync_tenant_system_schema(
            SyncTenantSystemSchemaCommandDTO(
                tenant_id=target.tenant_id,
                data_source_id=target.data_source_id,
                schema=target.schema,
            )
        )
        await session.commit()
        return result


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID value: {value}") from exc


def _resolve_manifest_path(raw_path: Path | None) -> Path | None:
    if raw_path is None:
        return None
    normalized = raw_path.expanduser().resolve()
    if not normalized.exists():
        raise FileNotFoundError(f"manifest file was not found: {normalized}")
    return normalized


def _to_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))

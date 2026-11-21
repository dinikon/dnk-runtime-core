"""Удалённые модули отсутствуют в API и новой начальной схеме."""

import ast
from contextlib import redirect_stderr
import io
import unittest
from pathlib import Path

from alembic.script import ScriptDirectory

from src.app_factory import create_app
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    managed_table_names,
    migration_metadata,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenant_persistence import HISTORICAL_TENANT_TABLE_NAMES

ROOT = Path(__file__).resolve().parents[1]


class ModuleRegistrationTests(unittest.TestCase):
    """Проверяет границы удаления и доступность оставшихся модулей."""

    def test_removed_source_modules_are_absent(self) -> None:
        """Backend и Console не содержат исходников удалённых модулей."""
        for relative in (
            "src/modules/warehousing",
            "src/modules/price_lists",
            "src/modules/currency",
            "src/management/commands/currency.py",
            "src/modules/reference_data/application/currency/query/get_currency_validation_catalog",
            "src/modules/reference_data/domain/currency/policy.py",
            "frontends/apps/console/src/modules/inventory",
            "frontends/apps/console/src/modules/price-lists",
            "src/config/feature/price_lists_config.py",
        ):
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_routes_include_neighbors_but_exclude_removed_modules(self) -> None:
        """OpenAPI содержит соседние модули без контрактов удалённых функций."""
        schema = create_app().openapi()
        paths = set(schema["paths"])
        for prefix in (
            "/api/console/inventory",
            "/api/console/warehousing",
            "/api/console/price-lists",
            "/api/console/price-list-offers",
            "/api/console/currency",
        ):
            self.assertFalse(any(path.startswith(prefix) for path in paths), prefix)
        self.assertEqual(
            {path for path in paths if path.startswith("/api/channels")},
            set(),
        )
        self.assertFalse(
            any(
                token in name.lower()
                for name in schema["components"]["schemas"]
                for token in ("pricelist", "partneroffer")
            )
        )
        self.assertFalse(
            any(
                {"price-lists", "price-list-offers"}.intersection(
                    operation.get("tags", ())
                )
                for methods in schema["paths"].values()
                for operation in methods.values()
            )
        )
        for prefix in (
            "/api/console/catalog",
            "/api/console/files",
            "/api/console/channels",
            "/api/console/crm/contacts",
            "/api/console/crm/companies",
            "/api/console/reference-data/currencies",
            "/api/console/tenants/current/currency-settings",
            "/api/console/auth/me",
        ):
            self.assertTrue(any(path.startswith(prefix) for path in paths), prefix)

    def test_metadata_excludes_retired_tables_and_retains_their_ownership(self) -> None:
        """Metadata содержит действующие таблицы, история сохраняет удалённые имена."""
        metadata = migration_metadata()
        tables = set(metadata.tables)
        self.assertLessEqual(tables, HISTORICAL_TENANT_TABLE_NAMES)
        retired_currency_tables = {
            "currency_exchange_rate_books",
            "currency_exchange_rate_quotes",
        }
        self.assertTrue(retired_currency_tables.isdisjoint(tables))
        self.assertLessEqual(retired_currency_tables, managed_table_names(metadata))
        self.assertTrue(
            {
                "catalog_item",
                "contacts",
                "companies",
                "files_registry",
                "users",
                "tenant_currency_settings",
                "channels",
                "channel_connections",
            }
            <= tables
        )
        self.assertTrue(
            {
                "skus",
                "warehouses",
                "catalog_products",
                "catalog_variants",
                "price_lists",
                "price_list_sync_runs",
                "price_list_sync_items",
                "partner_offers",
                "partner_offer_states",
            }.isdisjoint(tables)
        )
        self.assertFalse(any(name.startswith("warehousing_") for name in tables))

    def test_currency_cli_is_removed_and_reference_data_sync_remains(self) -> None:
        """CLI отвергает удалённую команду, сохраняя синхронизацию справочника."""
        from src.management.cli import build_parser

        parser = build_parser()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            parser.parse_args(["currency", "refresh"])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(
            parser.parse_args(
                ["reference-data", "sync", "--dataset", "currencies"]
            ).handler.__name__,
            "handle_sync",
        )

    def test_migrations_extend_independent_schema_baselines(self) -> None:
        """Каждая цепочка имеет свою baseline и линейные независимые продолжения."""
        configs = (
            (GlobalMigrator().config(), "global"),
            (TenantMigrator().config("dnk_test"), "tenant"),
        )
        for config, kind in configs:
            script = ScriptDirectory.from_config(config)
            revisions = list(script.walk_revisions())
            self.assertEqual(len(script.get_heads()), 1)
            self.assertEqual(revisions[-1].revision, f"0001_{kind}_baseline")
            self.assertIsNone(revisions[-1].down_revision)
            for index, revision in enumerate(revisions):
                if index + 1 < len(revisions):
                    self.assertEqual(
                        revision.down_revision, revisions[index + 1].revision
                    )
                tree = ast.parse(Path(revision.path).read_text())
                imports = [
                    n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                ]
                self.assertFalse(
                    any((name or "").startswith("src.") for name in imports)
                )

    def test_worker_and_configuration_do_not_depend_on_removed_modules(self) -> None:
        """CLI и конфигурация не зависят от удалённых модулей."""
        from src.config import dnk_config
        from src.management.cli import build_parser

        self.assertNotIn("CHANNELS", type(dnk_config).model_fields)
        self.assertIn("ENCRYPTION", type(dnk_config).model_fields)
        self.assertNotIn("PRICE_LISTS", type(dnk_config).model_fields)
        self.assertEqual(
            build_parser().parse_args(["jobs", "worker"]).handler.__name__,
            "handle_worker",
        )
        tree = ast.parse((ROOT / "src/management/commands/jobs.py").read_text())
        self.assertFalse(
            any(
                isinstance(n, ast.ImportFrom)
                and {"price_lists"}.intersection((n.module or "").split("."))
                for n in ast.walk(tree)
            )
        )

from __future__ import annotations

import unittest
from pathlib import Path

from src.modules.router import router as api_router
from src.modules.segmentation.presentation.depends import application, infrastructure
from src.modules.segmentation.presentation.http.router import router as segments_router

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SegmentationModuleSmokeTests(unittest.TestCase):
    def test_segments_router_is_importable_with_expected_prefix(self) -> None:
        self.assertEqual(segments_router.prefix, "/segments")
        self.assertEqual(segments_router.tags, ["segments"])

    def test_root_router_includes_segmentation_router(self) -> None:
        content = PROJECT_ROOT.joinpath("src/modules/router.py").read_text(
            encoding="utf-8"
        )

        self.assertEqual(api_router.prefix, "/api")
        self.assertIn("router as segmentation_router", content)
        self.assertIn("router.include_router(segmentation_router)", content)

    def test_dependency_placeholders_import_without_side_effects(self) -> None:
        self.assertEqual(application.__all__, [])
        self.assertEqual(infrastructure.__all__, [])

    def test_domain_aggregations_are_split_by_runtime_object(self) -> None:
        expected = {
            "segment_definition",
            "segment_version",
            "segment_static_member",
            "segment_snapshot",
            "segment_snapshot_member",
        }
        domain_path = PROJECT_ROOT / "src/modules/segmentation/domain"

        for aggregation in expected:
            aggregation_path = domain_path / aggregation
            self.assertTrue(aggregation_path.joinpath("entity.py").exists())
            self.assertTrue(aggregation_path.joinpath("value_object").is_dir())
            for value_object_path in aggregation_path.joinpath("value_object").glob(
                "*.py"
            ):
                if value_object_path.name == "__init__.py":
                    continue
                content = value_object_path.read_text(encoding="utf-8")
                self.assertEqual(content.count("\nclass "), 1)

        self.assertFalse(domain_path.joinpath("segment/entity.py").exists())
        self.assertFalse(domain_path.joinpath("segment/service.py").exists())
        self.assertFalse(domain_path.joinpath("segment/repository.py").exists())

    def test_application_aggregations_match_domain_aggregations(self) -> None:
        expected = {
            "segment_definition",
            "segment_version",
            "segment_static_member",
            "segment_snapshot",
            "segment_snapshot_member",
        }
        application_path = PROJECT_ROOT / "src/modules/segmentation/application"

        for aggregation in expected:
            aggregation_path = application_path / aggregation
            self.assertTrue(aggregation_path.is_dir())
            for package in ("command", "query", "dto", "use_case"):
                self.assertTrue(
                    aggregation_path.joinpath(package, "__init__.py").exists()
                )

        self.assertFalse(application_path.joinpath("segment/__init__.py").exists())
        self.assertFalse(application_path.joinpath("ports/__init__.py").exists())

    def test_http_aggregations_have_own_router_and_schema_packages(self) -> None:
        expected = {
            "segment_definition",
            "segment_version",
            "segment_static_member",
            "segment_snapshot",
            "segment_snapshot_member",
        }
        http_path = PROJECT_ROOT / "src/modules/segmentation/presentation/http"
        root_router = http_path.joinpath("router.py").read_text(encoding="utf-8")

        for aggregation in expected:
            aggregation_path = http_path / aggregation
            self.assertTrue(aggregation_path.joinpath("router.py").exists())
            self.assertTrue(aggregation_path.joinpath("controllers").is_dir())
            self.assertTrue(aggregation_path.joinpath("requests").is_dir())
            self.assertTrue(aggregation_path.joinpath("responses").is_dir())
            self.assertIn(f"{aggregation}.router", root_router)

        self.assertFalse(http_path.joinpath("segment/__init__.py").exists())
        self.assertFalse(http_path.joinpath("segment/requests.py").exists())
        self.assertFalse(http_path.joinpath("segment/responses.py").exists())


__all__ = ["SegmentationModuleSmokeTests"]

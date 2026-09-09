"""Verify direct Helm entrypoints, dependency integrity and packaged contents."""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("chart_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class PackageLayoutTests(unittest.TestCase):
    def test_root_chart_contains_its_own_templates(self):
        chart = build.verify(ROOT)
        self.assertIn(chart["name"], ["dnk-control-plane", "dnk-runtime-core"])
        self.assertTrue((ROOT / "templates/workloads.yaml").is_file())
        self.assertFalse(
            any(
                path.is_dir() and (path / "Chart.yaml").exists()
                for path in ROOT.iterdir()
            )
        )
        self.assertTrue(
            all(
                d["name"] in {"postgresql", "redis", "rabbitmq"}
                for d in chart["dependencies"]
            )
        )

    def test_missing_dependency_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "helm"
            shutil.copytree(ROOT, root)
            shutil.rmtree(root / "charts/redis")
            with self.assertRaisesRegex(ValueError, "Dependency set mismatch"):
                build.verify(root)

    def test_lock_version_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "helm"
            shutil.copytree(ROOT, root)
            path = root / "Chart.lock"
            path.write_text(
                path.read_text().replace("version: 0.1.0", "version: 9.0.0", 1)
            )
            with self.assertRaisesRegex(ValueError, "Chart.lock differs"):
                build.verify(root)

    def test_package_is_directly_installable_without_tooling_or_wrappers(self):
        before = build.directory_files(ROOT)
        chart = build.verify(ROOT)
        with tempfile.TemporaryDirectory() as destination:
            subprocess.run(
                [
                    __import__("sys").executable,
                    str(ROOT / "build.py"),
                    "--destination",
                    destination,
                ],
                check=True,
                capture_output=True,
            )
            (package,) = Path(destination).glob("*.tgz")
            with tarfile.open(package) as archive:
                names = {
                    name.removeprefix(chart["name"] + "/")
                    for name in archive.getnames()
                }
            self.assertIn("Chart.yaml", names)
            self.assertIn("templates/workloads.yaml", names)
            self.assertIn("templates/_gate.py.tpl", names)
            self.assertNotIn("build.py", names)
            self.assertFalse(
                any(
                    name.startswith(
                        (
                            "tests/",
                            "examples/",
                            "dnk-platform/",
                            "dnk-control-plane/",
                            "dnk-runtime-core/",
                        )
                    )
                    for name in names
                )
            )
        self.assertEqual(before, build.directory_files(ROOT))

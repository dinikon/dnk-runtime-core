"""Pinned archives are reproducible inputs and cannot silently change helper contracts."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("chart_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class DependencyTests(unittest.TestCase):
    def test_all_pinned_dependencies_verify(self):
        self.assertTrue(build.verify(ROOT))

    def test_changed_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "helm"
            shutil.copytree(ROOT, root)
            manifest = json.loads((root / "dependencies.lock.json").read_text())
            archive = root / manifest["artifacts"][0]["path"]
            archive.write_bytes(archive.read_bytes() + b"changed")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                build.verify(root)

    def test_common_content_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "helm"
            shutil.copytree(ROOT, root)
            manifest = json.loads((root / "dependencies.lock.json").read_text())
            manifest["common_content_sha256"] = "0" * 64
            (root / "dependencies.lock.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "identical content"):
                build.verify(root)

    def test_directory_and_archive_duplicate_is_rejected(self):
        files = {
            "Chart.yaml": b"name: parent\nversion: 1.0.0\ndependencies:\n- name: child\n  version: 1.0.0\n",
            "charts/child/Chart.yaml": b"name: child\nversion: 1.0.0\n",
            "charts/child-1.0.0.tgz": b"fixture",
        }
        with patch.object(
            build,
            "archive_files",
            return_value={"Chart.yaml": b"name: child\nversion: 1.0.0\n"},
        ):
            with self.assertRaisesRegex(ValueError, "Duplicate dependency"):
                build.verify_chart(files, set())

    def test_packaging_does_not_change_sources(self):
        before = build.directory_files(ROOT)
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
            self.assertTrue(list(Path(destination).glob("*.tgz")))
        self.assertEqual(before, build.directory_files(ROOT))

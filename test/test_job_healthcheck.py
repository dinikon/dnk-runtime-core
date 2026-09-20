import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from src.management.job_healthcheck import main


class JobHealthcheckTests(unittest.TestCase):
    def test_liveness_and_readiness_are_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat"
            ready = Path(str(path) + ".ready")
            with patch.dict(os.environ, {"SCHEDULED_JOBS__HEARTBEAT_PATH": str(path)}):
                self.assertEqual(main(["--liveness"]), 1)
                path.write_text(datetime.now(UTC).isoformat())
                self.assertEqual(main(["--liveness"]), 0)
                self.assertEqual(main([]), 1)
                ready.write_text(datetime.now(UTC).isoformat())
                self.assertEqual(main([]), 0)
                path.write_text((datetime.now(UTC) - timedelta(seconds=31)).isoformat())
                self.assertEqual(main(["--liveness"]), 1)
                path.write_text("corrupt")
                self.assertEqual(main(["--liveness"]), 1)
                path.write_text(datetime.now().isoformat())
                self.assertEqual(main(["--liveness"]), 1)

    def test_actual_cli_probe_does_not_import_application_or_database(self):
        script = """
import sys
from src.management.cli import main
try:
    main(['jobs','healthcheck','--liveness'])
except SystemExit as result:
    assert result.code == 0
assert 'sqlalchemy' not in sys.modules
assert 'src.config' not in sys.modules
assert 'asyncpg' not in sys.modules
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat"
            path.write_text(datetime.now(UTC).isoformat())
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=3,
                env=os.environ | {"SCHEDULED_JOBS__HEARTBEAT_PATH": str(path)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)

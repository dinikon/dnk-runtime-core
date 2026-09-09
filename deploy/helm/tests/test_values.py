"""The umbrella and standalone entrypoints must expose identical application defaults."""

from pathlib import Path
import unittest

import yaml

CHART = Path(__file__).resolve().parents[1] / "dnk-platform"


class ValuesDefaultsTest(unittest.TestCase):
    def test_application_defaults_match_standalone_charts(self):
        umbrella = yaml.safe_load((CHART / "values.yaml").read_text())
        for alias, name in [
            ("controlPlane", "dnk-control-plane"),
            ("runtime", "dnk-runtime-core"),
        ]:
            with self.subTest(package=alias):
                standalone = yaml.safe_load(
                    (CHART / "charts" / name / "values.yaml").read_text()
                )
                standalone.pop("global")
                self.assertEqual(umbrella[alias], standalone)


if __name__ == "__main__":
    unittest.main()

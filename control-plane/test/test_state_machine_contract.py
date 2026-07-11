import re
import unittest
from pathlib import Path

import yaml

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = CONTROL_PLANE_ROOT / "contracts" / "lifecycle" / "state-machines.yaml"
DOCUMENT_PATH = CONTROL_PLANE_ROOT / "docs" / "architecture" / "state-machines.md"


class StateMachineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_catalog_declares_required_machines(self) -> None:
        self.assertEqual(
            set(self.catalog["machines"]),
            {
                "tenant",
                "operation",
                "placement",
                "domain",
                "installation_actual",
                "owner_transfer",
                "agent_command",
            },
        )

    def test_transitions_only_reference_declared_states(self) -> None:
        for name, machine in self.catalog["machines"].items():
            with self.subTest(machine=name):
                states = set(machine["states"])
                terminal = set(machine["terminal"])
                self.assertIn(machine["initial"], states)
                self.assertLessEqual(terminal, states)

                identities: set[tuple[str, str]] = set()
                outgoing: set[str] = set()
                for transition in machine["transitions"]:
                    source = transition["from"]
                    target = transition["to"]
                    identity = (source, transition["event"])
                    self.assertIn(source, states)
                    self.assertIn(target, states)
                    self.assertNotIn(identity, identities)
                    identities.add(identity)
                    outgoing.add(source)

                self.assertTrue(terminal.isdisjoint(outgoing))

    def test_documented_arrow_transitions_exist_in_catalog(self) -> None:
        all_pairs = {
            (transition["from"], transition["to"])
            for machine in self.catalog["machines"].values()
            for transition in machine["transitions"]
        }
        document = DOCUMENT_PATH.read_text(encoding="utf-8")
        documented_pairs: set[tuple[str, str]] = set()
        for line in document.splitlines():
            if "→" not in line:
                continue
            parts = line.split("→")
            for left, right in zip(parts, parts[1:]):
                left_states = re.findall(r"\b[A-Z][A-Z_]+\b", left)
                right_states = re.findall(r"\b[A-Z][A-Z_]+\b", right)
                if left_states and right_states:
                    documented_pairs.add((left_states[-1], right_states[0]))

        self.assertTrue(documented_pairs)
        self.assertEqual(documented_pairs - all_pairs, set())


if __name__ == "__main__":
    unittest.main()

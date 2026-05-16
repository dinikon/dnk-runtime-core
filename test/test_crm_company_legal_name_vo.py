from __future__ import annotations

import unittest

from src.modules.crm.domain.company.error import InvalidCompanyLegalNameError
from src.modules.crm.domain.company.value_object import CompanyLegalNameVO


class CompanyLegalNameVOTests(unittest.TestCase):
    def test_normalizes_whitespace(self) -> None:
        legal_name = CompanyLegalNameVO("  Acme LLC  ")

        self.assertEqual(legal_name.value, "Acme LLC")

    def test_rejects_blank_string(self) -> None:
        with self.assertRaises(InvalidCompanyLegalNameError):
            CompanyLegalNameVO("   ")

    def test_rejects_non_string(self) -> None:
        with self.assertRaises(InvalidCompanyLegalNameError):
            CompanyLegalNameVO(None)  # type: ignore[arg-type]

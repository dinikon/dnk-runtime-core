from __future__ import annotations

import unittest
from uuid import uuid4

from src.modules.shared import EntityIdVO
from modules.shorter.infrastructure.infrastructure.services.link_code_generator import (
    LinkCodeGeneratorService,
)
from src.modules.shorter.domain.errors import (
    LinkCodeAlreadyExistsError,
    LinkCodeLengthNotSupportedError,
)
from src.modules.shorter.domain.template.service import (
    CreateTemplateCommand,
)
from modules.shorter.domain.template import TemplateCreateService
from src.modules.shorter.domain.template.value_object import (
    TemplateEntityTypeVO,
    TemplateTargetModuleTypeVO,
)


class _InMemoryLinkUniquenessChecker:
    def __init__(self, taken: set[tuple[str, str]] | None = None):
        self._taken = taken or set()
        self.calls: list[str] = []

    def exists_by_domain_and_code(self, *, domain_id: EntityIdVO, code: str) -> bool:
        self.calls.append(code)
        return (str(domain_id), code) in self._taken


class _DeterministicCodeGenerator:
    def __init__(self, values: list[str]):
        self._values = values
        self.lengths: list[int] = []

    def generate(self, *, length: int) -> str:
        self.lengths.append(length)
        return self._values.pop(0)

    def generate_8(self) -> str:
        return self.generate(length=8)


class TestTemplateCreateService(unittest.TestCase):
    def test_create_with_explicit_code(self) -> None:
        checker = _InMemoryLinkUniquenessChecker()
        service = TemplateCreateService(
            link_uniqueness_checker=checker,
            code_generator=_DeterministicCodeGenerator(values=["unused"]),
        )
        command = CreateTemplateCommand(
            created_by=EntityIdVO.from_value(uuid4()),
            domain_id=EntityIdVO.from_value(uuid4()),
            code="MyCode42",
            target_module=TemplateTargetModuleTypeVO.SHORTER,
            target_entity=TemplateEntityTypeVO.REDIRECT,
            target_entity_id=EntityIdVO.from_value(uuid4()),
        )

        result = service.create(command)

        self.assertEqual(result.link.code, "MyCode42")
        self.assertEqual(result.template.default_code, result.link.id)
        self.assertEqual(result.template.created_by, command.created_by)
        self.assertEqual(result.link.domain_id, command.domain_id)
        self.assertEqual(checker.calls, ["MyCode42"])

    def test_create_with_duplicate_explicit_code_raises(self) -> None:
        domain_id = EntityIdVO.from_value(uuid4())
        checker = _InMemoryLinkUniquenessChecker(taken={(str(domain_id), "dup12345")})
        service = TemplateCreateService(
            link_uniqueness_checker=checker,
            code_generator=_DeterministicCodeGenerator(values=["unused"]),
        )
        command = CreateTemplateCommand(
            created_by=EntityIdVO.from_value(uuid4()),
            domain_id=domain_id,
            code="dup12345",
            target_module=TemplateTargetModuleTypeVO.SHORTER,
            target_entity=TemplateEntityTypeVO.REDIRECT,
            target_entity_id=EntityIdVO.from_value(uuid4()),
        )

        with self.assertRaises(LinkCodeAlreadyExistsError):
            service.create(command)

    def test_create_without_code_generates_until_unique(self) -> None:
        domain_id = EntityIdVO.from_value(uuid4())
        checker = _InMemoryLinkUniquenessChecker(
            taken={
                (str(domain_id), "AAAA1111"),
                (str(domain_id), "BBBB2222"),
            }
        )
        generator = _DeterministicCodeGenerator(
            values=["AAAA1111", "BBBB2222", "CCCC3333"]
        )
        service = TemplateCreateService(
            link_uniqueness_checker=checker,
            code_generator=generator,
        )
        command = CreateTemplateCommand(
            created_by=EntityIdVO.from_value(uuid4()),
            domain_id=domain_id,
            code=None,
            target_module=TemplateTargetModuleTypeVO.SHORTER,
            target_entity=TemplateEntityTypeVO.REDIRECT,
            target_entity_id=EntityIdVO.from_value(uuid4()),
        )

        result = service.create(command)

        self.assertEqual(result.link.code, "CCCC3333")
        self.assertEqual(result.template.default_code, result.link.id)
        self.assertEqual(checker.calls, ["AAAA1111", "BBBB2222", "CCCC3333"])
        self.assertEqual(generator.lengths, [8, 8, 8])


class TestLinkCodeGeneratorService(unittest.TestCase):
    def test_generate_supported_lengths(self) -> None:
        generator = LinkCodeGeneratorService()
        for length in (4, 6, 8, 16):
            code = generator.generate(length=length)
            self.assertEqual(len(code), length)
            self.assertTrue(code.isalnum())

    def test_generate_with_unsupported_length_raises(self) -> None:
        generator = LinkCodeGeneratorService()
        with self.assertRaises(LinkCodeLengthNotSupportedError):
            generator.generate(length=5)


if __name__ == "__main__":
    unittest.main()

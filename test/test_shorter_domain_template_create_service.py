from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.shared import EntityIdVO
from src.modules.shorter.application.template.command.create_template import (
    CreateTemplateCommand,
)
from src.modules.shorter.application.template.use_case.create_template import (
    CreateTemplateUseCase,
)
from src.modules.shorter.domain.errors import (
    LinkCodeAlreadyExistsError,
    LinkCodeLengthNotSupportedError,
)
from src.modules.shorter.domain.link.entity import LinkEntity
from src.modules.shorter.domain.template.entity import TemplateEntity
from src.modules.shorter.domain.template.services import TemplateCreationService
from src.modules.shorter.domain.template.value_object import (
    TemplateEntityTypeVO,
    TemplateTargetModuleTypeVO,
)
from src.modules.shorter.infrastructure.services.random_link_code_generator import (
    RandomLinkCodeGenerator,
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


class _FixedClock:
    def __init__(self, now_value: datetime):
        self._now_value = now_value

    def now(self) -> datetime:
        return self._now_value


class _InMemoryTemplateRepository:
    def __init__(self):
        self.items: list[TemplateEntity] = []

    def save(self, template: TemplateEntity) -> None:
        self.items.append(template)


class _InMemoryLinkRepository:
    def __init__(self):
        self.items: list[LinkEntity] = []

    def save(self, link: LinkEntity) -> None:
        self.items.append(link)


class TestTemplateCreationService(unittest.TestCase):
    def test_create_with_explicit_code(self) -> None:
        checker = _InMemoryLinkUniquenessChecker()
        now = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
        service = TemplateCreationService(
            clock=_FixedClock(now),
            link_uniqueness_checker=checker,
            code_generator=_DeterministicCodeGenerator(values=["unused"]),
        )
        created_by = EntityIdVO.from_value(uuid4())
        domain_id = EntityIdVO.from_value(uuid4())
        target_entity_id = EntityIdVO.from_value(uuid4())

        result = service.create(
            created_by=created_by,
            domain_id=domain_id,
            code="MyCode42",
            target_module=TemplateTargetModuleTypeVO.SHORTER,
            target_entity=TemplateEntityTypeVO.REDIRECT,
            target_entity_id=target_entity_id,
        )

        self.assertEqual(result.link.code, "MyCode42")
        self.assertEqual(result.template.default_code, result.link.id)
        self.assertEqual(result.template.created_by, created_by)
        self.assertEqual(result.link.domain_id, domain_id)
        self.assertEqual(result.link.created_at, now)
        self.assertEqual(result.template.created_at, now)
        self.assertEqual(checker.calls, ["MyCode42"])

    def test_create_with_duplicate_explicit_code_raises(self) -> None:
        domain_id = EntityIdVO.from_value(uuid4())
        checker = _InMemoryLinkUniquenessChecker(taken={(str(domain_id), "dup12345")})
        now = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
        service = TemplateCreationService(
            clock=_FixedClock(now),
            link_uniqueness_checker=checker,
            code_generator=_DeterministicCodeGenerator(values=["unused"]),
        )

        with self.assertRaises(LinkCodeAlreadyExistsError):
            service.create(
                created_by=EntityIdVO.from_value(uuid4()),
                domain_id=domain_id,
                code="dup12345",
                target_module=TemplateTargetModuleTypeVO.SHORTER,
                target_entity=TemplateEntityTypeVO.REDIRECT,
                target_entity_id=EntityIdVO.from_value(uuid4()),
            )

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
        now = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
        service = TemplateCreationService(
            clock=_FixedClock(now),
            link_uniqueness_checker=checker,
            code_generator=generator,
        )

        result = service.create(
            created_by=EntityIdVO.from_value(uuid4()),
            domain_id=domain_id,
            code=None,
            target_module=TemplateTargetModuleTypeVO.SHORTER,
            target_entity=TemplateEntityTypeVO.REDIRECT,
            target_entity_id=EntityIdVO.from_value(uuid4()),
        )

        self.assertEqual(result.link.code, "CCCC3333")
        self.assertEqual(result.template.default_code, result.link.id)
        self.assertEqual(checker.calls, ["AAAA1111", "BBBB2222", "CCCC3333"])
        self.assertEqual(generator.lengths, [8, 8, 8])

    def test_create_service_rejects_invalid_attempts_limit(self) -> None:
        checker = _InMemoryLinkUniquenessChecker()
        generator = _DeterministicCodeGenerator(values=["AAAA1111"])
        now = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)

        with self.assertRaises(ValueError):
            TemplateCreationService(
                clock=_FixedClock(now),
                link_uniqueness_checker=checker,
                code_generator=generator,
                generation_attempts_limit=0,
            )


class TestCreateTemplateUseCase(unittest.TestCase):
    def test_execute_returns_dto_and_persists_entities(self) -> None:
        checker = _InMemoryLinkUniquenessChecker()
        generator = _DeterministicCodeGenerator(values=["UVWX7788"])
        now = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
        service = TemplateCreationService(
            clock=_FixedClock(now),
            link_uniqueness_checker=checker,
            code_generator=generator,
        )
        template_repository = _InMemoryTemplateRepository()
        link_repository = _InMemoryLinkRepository()
        use_case = CreateTemplateUseCase(
            service=service,
            template_repository=template_repository,
            link_repository=link_repository,
        )
        command = CreateTemplateCommand(
            created_by=uuid4(),
            domain_id=uuid4(),
            code=None,
            target_module="SHORTER",
            target_entity="redirect",
            target_entity_id=uuid4(),
        )

        result = use_case.execute(command)

        self.assertEqual(result.code, "UVWX7788")
        self.assertEqual(result.domain_id, command.domain_id)
        self.assertEqual(len(template_repository.items), 1)
        self.assertEqual(len(link_repository.items), 1)
        self.assertEqual(template_repository.items[0].id.value, result.template_id)
        self.assertEqual(link_repository.items[0].id.value, result.link_id)


class TestRandomLinkCodeGenerator(unittest.TestCase):
    def test_generate_supported_lengths(self) -> None:
        generator = RandomLinkCodeGenerator()
        for length in (4, 6, 8, 16):
            code = generator.generate(length=length)
            self.assertEqual(len(code), length)
            self.assertTrue(code.isalnum())

    def test_generate_with_unsupported_length_raises(self) -> None:
        generator = RandomLinkCodeGenerator()
        with self.assertRaises(LinkCodeLengthNotSupportedError):
            generator.generate(length=5)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import UUID, uuid4

from src.modules.shared.depends import UuidDep, get_uuid_generator
from src.modules.shared.depends.uuid import default_uuid_generator
from src.modules.shared.infrastructure.uuid import Uuid7Generator


class _UuidGeneratorStub:
    def __init__(self) -> None:
        self.value = uuid4()

    def new_uuid(self) -> UUID:
        return self.value


class SharedUuidServiceTests(unittest.TestCase):
    def test_uuid7_generator_returns_uuid(self) -> None:
        value = Uuid7Generator().new_uuid()

        self.assertIsInstance(value, UUID)

    def test_get_uuid_generator_uses_app_state_override(self) -> None:
        override = _UuidGeneratorStub()
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(uuid_generator=override))
        )

        self.assertIs(get_uuid_generator(request), override)

    def test_get_uuid_generator_uses_default_without_override(self) -> None:
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

        self.assertIs(get_uuid_generator(request), default_uuid_generator)

    def test_shared_depends_exports_uuid_dependency(self) -> None:
        self.assertIsNotNone(UuidDep)


__all__ = ["SharedUuidServiceTests"]

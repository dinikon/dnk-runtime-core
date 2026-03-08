import unittest
import uuid

from src.modules.shared.db.types.string_uuid import StringUUID


class _DummyDialect:
    def __init__(self, name: str):
        self.name = name


class _UuidLikeValue:
    def __init__(self, value: uuid.UUID):
        self._value = value

    def __str__(self) -> str:
        return str(self._value)


class StringUUIDTypeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._type = StringUUID()
        self._postgres = _DummyDialect("postgresql")
        self._sqlite = _DummyDialect("sqlite")

    def test_process_result_value_accepts_uuid_like_object(self) -> None:
        expected = uuid.uuid4()

        actual = self._type.process_result_value(
            _UuidLikeValue(expected),
            self._postgres,
        )

        self.assertEqual(actual, expected)

    def test_process_bind_param_normalizes_string_for_postgresql(self) -> None:
        expected = uuid.uuid4()

        actual = self._type.process_bind_param(str(expected), self._postgres)

        self.assertEqual(actual, expected)

    def test_process_bind_param_returns_string_for_sqlite(self) -> None:
        expected = uuid.uuid4()

        actual = self._type.process_bind_param(expected, self._sqlite)

        self.assertEqual(actual, str(expected))

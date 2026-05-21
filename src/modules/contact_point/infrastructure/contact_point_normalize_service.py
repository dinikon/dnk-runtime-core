from __future__ import annotations

import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

from src.modules.contact_point.application.ports import ContactPointNormalizerPort
from src.modules.contact_point.domain.contact_point import (
    ContactPointTypeVO,
    InvalidContactPointValueError,
    UnsupportedContactPointTypeError,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactPointNormalizeService(ContactPointNormalizerPort):
    def normalize(
        self,
        *,
        contact_point_type: ContactPointTypeVO,
        raw_value: str,
    ) -> str:
        if contact_point_type == ContactPointTypeVO.EMAIL:
            return self._normalize_email(raw_value)
        if contact_point_type == ContactPointTypeVO.PHONE:
            return self._normalize_phone(raw_value)
        raise UnsupportedContactPointTypeError(str(contact_point_type))

    @staticmethod
    def _normalize_email(raw_value: str) -> str:
        value = raw_value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise InvalidContactPointValueError(
                ContactPointTypeVO.EMAIL.value, raw_value
            )
        return value

    @staticmethod
    def _normalize_phone(raw_value: str) -> str:
        value = raw_value.strip()
        if not value.startswith("+"):
            raise InvalidContactPointValueError(
                ContactPointTypeVO.PHONE.value, raw_value
            )

        try:
            parsed = phonenumbers.parse(value, None)
        except NumberParseException as exc:
            raise InvalidContactPointValueError(
                ContactPointTypeVO.PHONE.value, raw_value
            ) from exc

        if parsed.extension or not phonenumbers.is_valid_number(parsed):
            raise InvalidContactPointValueError(
                ContactPointTypeVO.PHONE.value, raw_value
            )

        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


__all__ = ["ContactPointNormalizeService"]

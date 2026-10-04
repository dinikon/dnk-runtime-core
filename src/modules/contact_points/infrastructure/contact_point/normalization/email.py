from email_validator import validate_email, EmailNotValidError
from src.modules.contact_points.domain.contact_point.error import (
    InvalidContactPointError,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointValueVO,
    NormalizedContactPoint,
    NormalizationContext,
)


class EmailNormalizer:
    """Проверяет синтаксис email, сохраняя регистр локальной части."""

    def normalize(
        self, value: str, context: NormalizationContext
    ) -> NormalizedContactPoint:
        """Нормализует домен без DNS-проверок и provider-specific правил."""
        try:
            result = validate_email(value.strip(), check_deliverability=False)
        except EmailNotValidError as exc:
            raise InvalidContactPointError(
                "Введите email в формате name@domain.com."
            ) from exc
        return NormalizedContactPoint(ContactPointValueVO(result.normalized))


__all__ = ["EmailNormalizer"]

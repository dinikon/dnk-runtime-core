import re
import phonenumbers
from src.modules.contact_points.domain.contact_point.error import (
    InvalidContactPointError,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointValueVO,
    NormalizedContactPoint,
    NormalizationContext,
)


class PhoneNormalizer:
    """Проверяет полный номер для выбранной страны и возвращает E.164."""

    def normalize(
        self, value: str, context: NormalizationContext
    ) -> NormalizedContactPoint:
        """Нормализует без сетевого запроса и проверки владения."""
        region = (context.country_code or "").upper()
        if region not in phonenumbers.SUPPORTED_REGIONS:
            raise InvalidContactPointError("Выберите страну телефона.", "country_code")
        # The UI accepts a whole phone value, not a number extracted from free text.
        if not re.fullmatch(r"\+?[\d\s().-]+", value.strip()):
            raise InvalidContactPointError("Введите корректный номер телефона.")
        try:
            number = phonenumbers.parse(value.strip(), region)
        except phonenumbers.NumberParseException as exc:
            raise InvalidContactPointError(
                "Введите корректный номер телефона."
            ) from exc
        if number.extension or not phonenumbers.is_valid_number_for_region(
            number, region
        ):
            raise InvalidContactPointError(
                "Номер не соответствует выбранной стране или содержит добавочный номер."
            )
        canonical = phonenumbers.format_number(
            number, phonenumbers.PhoneNumberFormat.E164
        )
        return NormalizedContactPoint(ContactPointValueVO(canonical), region)


__all__ = ["PhoneNormalizer"]

from enum import StrEnum


class ReturnDirection(StrEnum):
    """Различает приёмку от получателя и отправку поставщику."""

    FROM_RECIPIENT = "FROM_RECIPIENT"
    TO_SUPPLIER = "TO_SUPPLIER"

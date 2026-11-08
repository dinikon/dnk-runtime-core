from decimal import Decimal


def is_decimal_multiple(value: Decimal, step: Decimal) -> bool:
    """Проверяет точную кратность конечного неотрицательного значения положительному шагу."""
    if value.is_zero():
        return True
    coefficient, exponent = _decimal_parts(value)
    step_coefficient, step_exponent = _decimal_parts(step)
    difference = exponent - step_exponent
    # Модульная степень сохраняет точность без разворачивания больших порядков.
    return (
        difference >= 0
        and (coefficient * pow(10, difference, step_coefficient)) % step_coefficient
        == 0
    )


def _decimal_parts(value: Decimal) -> tuple[int, int]:
    """Выделяет целый коэффициент и порядок без конечных нулей."""
    parts = value.as_tuple()
    digits = list(parts.digits)
    exponent = int(parts.exponent)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    return coefficient, exponent

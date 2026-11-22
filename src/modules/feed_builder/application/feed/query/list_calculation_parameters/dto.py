from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CalculationParameterDTO:
    """Описывает реально подключённый параметр и его тип."""

    id: str
    label: str
    value_type: str
    nullable: bool


@dataclass(frozen=True, slots=True)
class ListCalculationParametersResultDTO:
    """Передаёт закрытый реестр параметров Catalog."""

    items: tuple[CalculationParameterDTO, ...]

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StatusTransitionDTO:
    """Передаёт допустимые цели одного исходного состояния."""

    source_status: str
    target_statuses: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GetStatusTransitionsResultDTO:
    """Передаёт полную матрицу без правил в транспортном слое."""

    items: tuple[StatusTransitionDTO, ...]

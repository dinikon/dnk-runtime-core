from dataclasses import dataclass
from src.modules.channels.application.plugin_contract import (
    ReadPublicationDetailsInputDTO,
    PublicationTranslationDTO,
)


@dataclass(frozen=True, slots=True)
class InspectContentUpdateInputDTO:
    """Адресует одну существующую цель и предлагаемые тексты без произвольного payload."""

    target: ReadPublicationDetailsInputDTO
    desired: tuple[PublicationTranslationDTO, ...]


@dataclass(frozen=True, slots=True)
class InspectContentUpdateOutcomeDTO:
    """Возвращает фактические тексты и явные ограничения записи."""

    observed: tuple[PublicationTranslationDTO, ...]
    issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SendContentUpdateInputDTO:
    """Ограничивает запись подтверждёнными текстами существующей цели."""

    inspection: InspectContentUpdateInputDTO
    expected_observed_hash: str


@dataclass(frozen=True, slots=True)
class SendContentUpdateOutcomeDTO:
    """Отмечает принятие записи; подтверждение выполняется отдельным чтением."""

    accepted: bool

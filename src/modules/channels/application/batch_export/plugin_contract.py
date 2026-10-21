from dataclasses import dataclass
from typing import BinaryIO, Protocol
from src.modules.channels.application.plugin_contract import ResourceSettingsDTO
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


@dataclass(frozen=True, slots=True)
class ExportInspectionDTO:
    """Передаёт ключ сопоставления и неизменяемые поля карточки без native payload."""

    identity_key: str | None
    baseline: dict[str, JsonValue]
    issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExportIdentityDTO:
    """Описывает наблюдаемую пару native ID/ключ файла для полного обхода."""

    external_id: str
    identity_key: str | None
    baseline: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ExportIdentityPageDTO:
    """Ограничивает один сетевой шаг пагинируемым обходом источника."""

    items: tuple[ExportIdentityDTO, ...]
    cursor: str | None
    complete: bool


@dataclass(frozen=True, slots=True)
class ExportPollDTO:
    """Отделяет завершение внешнего процесса от доказательства записи текстов."""

    finished: bool
    failed: bool = False


class BatchExportPlugin(Protocol):
    """SDK пакетной отправки: provider владеет форматом, ядро — доставкой и расписанием."""

    async def inspect(
        self, settings: ResourceSettingsDTO, item: ExportItemVO
    ) -> ExportInspectionDTO:
        """Читает целевую карточку до формирования файла."""
        ...

    async def identities(
        self, settings: ResourceSettingsDTO, cursor: str | None
    ) -> ExportIdentityPageDTO:
        """Читает одну страницу всех внешних идентификаторов для проверки коллизий."""
        ...

    def begin(self, target: BinaryIO) -> None:
        """Открывает поток подготовленного фида."""
        ...

    def append(self, target: BinaryIO, item: ExportItemVO) -> None:
        """Сериализует один зафиксированный снимок без обращений к каталогу."""
        ...

    def end(self, target: BinaryIO) -> None:
        """Закрывает валидный документ."""
        ...

    async def submit(self, settings: ResourceSettingsDTO, url: str) -> str:
        """Однократно передаёт URL и возвращает непрозрачный ID импорта."""
        ...

    async def poll(self, remote_id: str) -> ExportPollDTO:
        """Читает состояние уже принятого импорта."""
        ...

    async def verify(
        self, settings: ResourceSettingsDTO, item: ExportItemVO
    ) -> tuple[str, ...]:
        """Сверяет тексты и остальные значимые поля исходного native ID."""
        ...

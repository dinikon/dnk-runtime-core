from dataclasses import dataclass
from src.modules.channels.domain.batch_export.value_object.item import ExportItemVO


@dataclass(frozen=True, slots=True)
class PrepareExportArtifactPageResultDTO:
    """Отличает пустой конец снимка от отозванного допуска операции."""

    items: tuple[ExportItemVO, ...]
